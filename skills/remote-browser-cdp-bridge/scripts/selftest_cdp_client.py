# Self-test for scripts/cdp_client.py — run against a live bridge.

`python scripts/selftest_cdp_client.py <cdp_url>`

Checks that each helper actually does what its name claims, so the client is never
trusted on a first real task. Uses an own tab and closes it afterwards.

Exit 0 = all pass. Any FAIL means the client, not the site, is the problem.
