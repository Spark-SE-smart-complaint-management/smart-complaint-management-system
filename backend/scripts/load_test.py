"""Reproducible smoke load for SRS read and complaint-submission targets.

Example: python scripts/load_test.py --concurrency 500 --requests 500
Set LOAD_TEST_EMAIL and LOAD_TEST_PASSWORD to a synthetic admin account.
"""

import argparse
import asyncio
import os
import sys
import time
import uuid

import httpx


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.getenv("LOAD_TEST_BASE_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--submit-count", type=int, default=0)
    args = parser.parse_args()
    email = os.getenv("LOAD_TEST_EMAIL", "")
    password = os.getenv("LOAD_TEST_PASSWORD", "")
    if not email or not password:
        parser.error(
            "Set LOAD_TEST_EMAIL and LOAD_TEST_PASSWORD to a synthetic admin account"
        )
    if args.concurrency < 1 or args.requests < 1 or args.submit_count < 0:
        parser.error(
            "concurrency and requests must be positive; submit-count cannot be negative"
        )

    timeout = httpx.Timeout(15.0, connect=5.0)
    limits = httpx.Limits(
        max_connections=max(args.concurrency, 20),
        max_keepalive_connections=max(args.concurrency, 20),
    )
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"), timeout=timeout, limits=limits
    ) as client:
        login = await client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        if login.status_code != 200:
            print(f"Login failed: HTTP {login.status_code}", file=sys.stderr)
            return 2
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        semaphore = asyncio.Semaphore(args.concurrency)
        samples: list[float] = []
        failures: list[str] = []

        async def request(path: str, method: str = "GET", json_body=None):
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.request(
                        method, path, headers=headers, json=json_body
                    )
                    elapsed = time.perf_counter() - started
                    samples.append(elapsed)
                    if response.status_code >= 400:
                        failures.append(f"{method} {path}: HTTP {response.status_code}")
                    return response
                except Exception as exc:  # keep a concise, reproducible failure record
                    samples.append(time.perf_counter() - started)
                    failures.append(f"{method} {path}: {type(exc).__name__}: {exc}")

        tasks = []
        for _ in range(args.requests):
            tasks.extend(
                [
                    request("/health"),
                    request("/reports/dashboard"),
                    request("/notifications?limit=20"),
                ]
            )
        read_started = time.perf_counter()
        await asyncio.gather(*tasks)
        read_wall = time.perf_counter() - read_started
        read_samples = samples[:]

        submit_samples: list[float] = []

        async def submit(index: int):
            started = time.perf_counter()
            title = f"Load test {uuid.uuid4().hex[:12]}"
            await request(
                "/complaints",
                method="POST",
                json_body={
                    "title": title,
                    "description": f"Synthetic load record {index} {uuid.uuid4().hex}",
                },
            )
            submit_samples.append(time.perf_counter() - started)

        if args.submit_count:
            await asyncio.gather(*(submit(index) for index in range(args.submit_count)))

    def percentile(values: list[float], fraction: float) -> float:
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]

    read_p95 = percentile(read_samples, 0.95) if read_samples else 0
    max_submit = max(submit_samples, default=0)
    print(f"Concurrency: {args.concurrency}; requests per route: {args.requests}")
    print(
        f"Read requests: {len(read_samples)}; wall time: {read_wall:.3f}s; p95: {read_p95:.3f}s; max: {max(read_samples, default=0):.3f}s"
    )
    print(f"Complaint submissions: {len(submit_samples)}; max: {max_submit:.3f}s")
    print(f"Failures: {len(failures)}")
    for failure in failures[:20]:
        print(f"- {failure}")
    passed = not failures and max(read_samples, default=0) <= 3.0 and max_submit <= 2.0
    print("SRS target check: PASS" if passed else "SRS target check: FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
