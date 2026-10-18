# aux-5xx-failover — Hermes 用户插件模板
#
# 安装（每个 Hermes 实例/容器都要装一份，插件不跨容器）：
#   mkdir -p /opt/data/plugins/aux-5xx-failover
#   把本文件复制为 /opt/data/plugins/aux-5xx-failover/__init__.py
#   同目录写 plugin.yaml（见下方 YAML 注释）
#   /opt/hermes/bin/hermes plugins enable aux-5xx-failover
#   /opt/hermes/bin/hermes plugins list | grep aux-5xx   # 应显示 enabled
#
# plugin.yaml 内容：
#   name: aux-5xx-failover
#   version: 1.0.0
#   description: "Treat HTTP 5xx from an auxiliary provider as a capacity failure so Hermes
#     fails over to auxiliary.<task>.fallback_chain instead of retrying the same dead provider."
#   provides_hooks:
#     - transform_api_error_classification
#
# 生效验证：起一个本地假 503 服务，临时把 auxiliary.vision.base_url 指过去，
# 再调 vision_analyze；能拿到备用模型的答案 = 生效。测完删掉临时 base_url。
"""Make HTTP 5xx (503 resource pressure, 502, 504...) a fallback-triggering capacity failure.

Why: Hermes' auxiliary client retries a 5xx on the SAME provider, then raises. The recovery
ladder only hops to another provider when the error matches ``_FALLBACK_REASONS``, a table with
auth/payment/rate-limit/timeout/connection entries but no 5xx entry. A provider stuck at
"HTTP 503: Service temporarily unavailable due to resource pressure" therefore leaves
tasks like vision_analyze with no fallback: N retry cycles, then "Automatic recovery gave up".

Patches (process-level, applied at plugin load):
1. append a 5xx predicate to ``agent.auxiliary_client._FALLBACK_REASONS``;
2. quarantine a 5xx-failing candidate briefly (180s), not for the long default TTL;
3. register ``transform_api_error_classification`` so the main classifier treats 5xx as
   ``resource_pressure`` with ``should_fallback``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_PATCH_FLAG = "_xiaoka_5xx_failover_installed"
_TRANSIENT_TTL_SECONDS = 180.0


def _status_of(exc) -> int:
    """HTTP status from an exception, tolerating openai/pydantic wrappers."""
    code = getattr(exc, "status_code", None)
    if code is None:
        code = getattr(getattr(exc, "response", None), "status_code", None)
    if code is None:
        candidate = getattr(exc, "code", None)
        code = candidate if isinstance(candidate, int) else None
    try:
        return int(code)
    except (TypeError, ValueError):
        return 0


def _is_5xx(exc) -> bool:
    return 500 <= _status_of(exc) <= 599


def install() -> bool:
    """Apply the auxiliary-client patch once per process."""
    try:
        from agent import auxiliary_client as ac
    except Exception:
        logger.debug("aux-5xx-failover: auxiliary_client not importable yet", exc_info=True)
        return False

    if getattr(ac, _PATCH_FLAG, False):
        return True

    try:
        reasons = tuple(ac._FALLBACK_REASONS)
        if not any(label == "server error" for _, label in reasons):
            ac._FALLBACK_REASONS = reasons + ((_is_5xx, "server error"),)
        try:
            from agent import auxiliary_health as ah
            ah._CANDIDATE_QUARANTINE_TTL.setdefault("server error", _TRANSIENT_TTL_SECONDS)
        except Exception:
            logger.debug("aux-5xx-failover: quarantine TTL patch skipped", exc_info=True)
        setattr(ac, _PATCH_FLAG, True)
        logger.info("aux-5xx-failover: 5xx now triggers auxiliary provider fallback")
        return True
    except Exception:
        logger.warning("aux-5xx-failover: patch failed", exc_info=True)
        return False


def _classify(*, status_code=None, error=None, error_message="", **_ignored):
    """Hook: main classifier override for 5xx. Declines anything else."""
    code = status_code
    if code is None and error is not None:
        code = _status_of(error)
    try:
        code = int(code or 0)
    except (TypeError, ValueError):
        code = 0
    if not 500 <= code <= 599:
        return None
    return {"reason": "resource_pressure", "retryable": True, "should_fallback": True}


def register(ctx) -> None:
    """Plugin entry point."""
    install()
    try:
        ctx.register_hook("transform_api_error_classification", _classify)
    except Exception:
        logger.warning("aux-5xx-failover: hook registration failed", exc_info=True)
