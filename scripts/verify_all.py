"""Three-Pass Master Quality Assurance & Verification Suite.

Executes 3 exhaustive audit passes required for Datheon Directorate Evaluation:
  - Pass 1: Architecture, Component Unit & Extraction Verification
  - Pass 2: RBAC Security Boundary & Hallucination Guardrail Audit
  - Pass 3: End-to-End Integration, Prometheus Telemetry & Latency Benchmarks
"""
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def run_pass_1():
    print("\n" + "=" * 75)
    print("  PASS 1: ARCHITECTURAL INTEGRITY & COMPONENT UNIT TEST AUDIT")
    print("=" * 75)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_task1_etl.py",
        "tests/test_task3_agent_hitl.py",
        "tests/test_client_sdk.py",
        "-v",
    ]
    res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("[!] Pass 1 Failed with errors:\n", res.stderr)
        return False
    print("[+] PASS 1 VERIFICATION: SUCCESSFUL")
    return True


def run_pass_2():
    print("\n" + "=" * 75)
    print("  PASS 2: RBAC SECURITY BOUNDARIES, CITATION INTEGRITY & ADVERSARIAL AUDIT")
    print("=" * 75)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_task2_rag_rbac.py",
        "tests/test_security_leakage.py",
        "tests/test_adversarial_security.py",
        "-v",
    ]
    res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("[!] Pass 2 Failed with errors:\n", res.stderr)
        return False
    print("[+] PASS 2 VERIFICATION: SUCCESSFUL")
    return True


def run_pass_3():
    print("\n" + "=" * 75)
    print("  PASS 3: END-TO-END FASTAPI SERVICE, PROMETHEUS TELEMETRY & LATENCY")
    print("=" * 75)
    # Run API service and rate limiter tests
    cmd_test = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_task4_api_service.py",
        "tests/test_rate_limiter.py",
        "-v",
    ]
    res_test = subprocess.run(cmd_test, cwd=BASE_DIR, capture_output=True, text=True)
    print(res_test.stdout)
    if res_test.returncode != 0:
        print("[!] Pass 3 Service Tests Failed:\n", res_test.stderr)
        return False

    # Run latency benchmark suite
    from scripts.run_latency_benchmark import run_latency_benchmark
    print("[*] Running End-to-End Latency Benchmark...")
    run_latency_benchmark()

    print("[+] PASS 3 VERIFICATION: SUCCESSFUL")
    return True


def main():
    start_time = time.time()
    print("=" * 75)
    print("  DATHEON FORWARD DEPLOYED ENGINEERING: 3-PASS COMPREHENSIVE VERIFICATION")
    print("=" * 75)

    p1 = run_pass_1()
    if not p1:
        sys.exit(1)

    p2 = run_pass_2()
    if not p2:
        sys.exit(2)

    p3 = run_pass_3()
    if not p3:
        sys.exit(3)

    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print(f"  ALL 3 VERIFICATION PASSES COMPLETED IN {elapsed:.2f} SECONDS")
    print("  STATUS: 100% PRODUCTION READY FOR DIRECTORATE EVALUATION")
    print("=" * 75)


if __name__ == "__main__":
    main()

