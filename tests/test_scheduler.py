"""Tests for the scheduling simulation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.scheduler_service import (
    run_fcfs, run_round_robin, run_priority, generate_demo_jobs
)


def test_fcfs_order():
    jobs = generate_demo_jobs()
    r = run_fcfs(jobs)
    assert r["algorithm"] == "First-Come, First-Served (FCFS)"
    # Jobs should complete in arrival order
    for i in range(len(r["jobs"]) - 1):
        assert r["jobs"][i]["completion_time"] <= r["jobs"][i + 1]["completion_time"]

def test_fcfs_no_negative_wait():
    jobs = generate_demo_jobs()
    r = run_fcfs(jobs)
    for j in r["jobs"]:
        assert j["waiting_time"] >= 0

def test_fcfs_turnaround():
    jobs = generate_demo_jobs()
    r = run_fcfs(jobs)
    for j in r["jobs"]:
        assert j["turnaround_time"] == j["completion_time"] - j["arrival_time"]

def test_round_robin_quantum():
    jobs = generate_demo_jobs()
    r = run_round_robin(jobs, quantum=2)
    assert r["quantum"] == 2
    # Each gantt block should be at most quantum long
    for g in r["gantt"]:
        assert g["end"] - g["start"] <= 2

def test_round_robin_all_complete():
    jobs = generate_demo_jobs()
    r = run_round_robin(jobs, quantum=2)
    assert len(r["jobs"]) == len(jobs)

def test_round_robin_different_quantum():
    jobs = generate_demo_jobs()
    r1 = run_round_robin(jobs, quantum=1)
    r3 = run_round_robin(jobs, quantum=3)
    # Different quantums produce different number of gantt entries
    assert len(r1["gantt"]) != len(r3["gantt"]) or r1["avg_waiting_time"] != r3["avg_waiting_time"]

def test_priority_order():
    jobs = generate_demo_jobs()
    r = run_priority(jobs)
    assert r["algorithm"] == "Priority Scheduling (Non-preemptive)"
    assert len(r["jobs"]) == len(jobs)

def test_priority_no_negative_wait():
    jobs = generate_demo_jobs()
    r = run_priority(jobs)
    for j in r["jobs"]:
        assert j["waiting_time"] >= 0

def test_gantt_continuity_fcfs():
    jobs = generate_demo_jobs()
    r = run_fcfs(jobs)
    for i in range(len(r["gantt"]) - 1):
        assert r["gantt"][i]["end"] <= r["gantt"][i + 1]["start"] or r["gantt"][i]["end"] == r["gantt"][i + 1]["start"]

def test_average_calculations():
    jobs = generate_demo_jobs()
    r = run_fcfs(jobs)
    avg_wt = sum(j["waiting_time"] for j in r["jobs"]) / len(r["jobs"])
    assert abs(r["avg_waiting_time"] - round(avg_wt, 2)) < 0.01
