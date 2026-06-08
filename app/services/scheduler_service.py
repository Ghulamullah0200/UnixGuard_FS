"""
scheduler_service.py — CPU scheduling simulation for educational purposes.

Implements three scheduling algorithms:
  1. First-Come, First-Served (FCFS)
  2. Round Robin (RR) with configurable time quantum
  3. Priority Scheduling (non-preemptive)

Generates demo scan jobs and computes:
  - Execution order
  - Waiting time
  - Turnaround time
  - Completion time
  - Gantt chart data
"""

from typing import List, Optional
from copy import deepcopy


def generate_demo_jobs() -> List[dict]:
    """Generate a set of demo scan jobs that simulate audit tasks."""
    return [
        {"job_id": 1, "name": "Scan /home",   "burst_time": 4, "priority": 3, "arrival_time": 0},
        {"job_id": 2, "name": "Scan /etc",    "burst_time": 2, "priority": 1, "arrival_time": 1},
        {"job_id": 3, "name": "Scan /var",    "burst_time": 5, "priority": 4, "arrival_time": 2},
        {"job_id": 4, "name": "Scan /shared", "burst_time": 3, "priority": 2, "arrival_time": 3},
        {"job_id": 5, "name": "Scan /tmp",    "burst_time": 1, "priority": 5, "arrival_time": 4},
    ]


def run_fcfs(jobs: List[dict]) -> dict:
    """
    First-Come, First-Served scheduling.
    Jobs are processed in order of arrival time.
    """
    sorted_jobs = sorted(jobs, key=lambda j: (j["arrival_time"], j["job_id"]))
    results = []
    gantt = []
    current_time = 0

    for job in sorted_jobs:
        start_time = max(current_time, job["arrival_time"])
        completion_time = start_time + job["burst_time"]
        waiting_time = start_time - job["arrival_time"]
        turnaround_time = completion_time - job["arrival_time"]

        results.append({
            "job_id": job["job_id"],
            "name": job["name"],
            "arrival_time": job["arrival_time"],
            "burst_time": job["burst_time"],
            "start_time": start_time,
            "completion_time": completion_time,
            "waiting_time": waiting_time,
            "turnaround_time": turnaround_time,
            "priority": job["priority"],
        })

        gantt.append({
            "job_id": job["job_id"],
            "name": job["name"],
            "start": start_time,
            "end": completion_time,
        })

        current_time = completion_time

    avg_wt = sum(r["waiting_time"] for r in results) / len(results) if results else 0
    avg_tat = sum(r["turnaround_time"] for r in results) / len(results) if results else 0

    return {
        "algorithm": "First-Come, First-Served (FCFS)",
        "quantum": None,
        "jobs": results,
        "gantt": gantt,
        "avg_waiting_time": round(avg_wt, 2),
        "avg_turnaround_time": round(avg_tat, 2),
    }


def run_round_robin(jobs: List[dict], quantum: int = 2) -> dict:
    """
    Round Robin scheduling with configurable time quantum.
    Jobs are processed in FIFO order, each getting at most 'quantum' time units.
    """
    sorted_jobs = sorted(jobs, key=lambda j: (j["arrival_time"], j["job_id"]))
    remaining = {j["job_id"]: j["burst_time"] for j in sorted_jobs}
    first_start = {j["job_id"]: None for j in sorted_jobs}
    completion = {}
    queue = []
    gantt = []
    current_time = 0
    job_map = {j["job_id"]: j for j in sorted_jobs}

    # Add initially available jobs
    arrived = set()
    for j in sorted_jobs:
        if j["arrival_time"] <= current_time:
            queue.append(j["job_id"])
            arrived.add(j["job_id"])

    max_iter = sum(j["burst_time"] for j in sorted_jobs) + len(sorted_jobs) * 10
    iteration = 0

    while queue and iteration < max_iter:
        iteration += 1
        job_id = queue.pop(0)

        if first_start[job_id] is None:
            first_start[job_id] = current_time

        exec_time = min(quantum, remaining[job_id])
        gantt.append({
            "job_id": job_id,
            "name": job_map[job_id]["name"],
            "start": current_time,
            "end": current_time + exec_time,
        })

        current_time += exec_time
        remaining[job_id] -= exec_time

        # Add newly arrived jobs
        for j in sorted_jobs:
            if j["job_id"] not in arrived and j["arrival_time"] <= current_time:
                queue.append(j["job_id"])
                arrived.add(j["job_id"])

        if remaining[job_id] > 0:
            queue.append(job_id)
        else:
            completion[job_id] = current_time

    # Build results
    results = []
    for j in sorted_jobs:
        ct = completion.get(j["job_id"], current_time)
        tat = ct - j["arrival_time"]
        wt = tat - j["burst_time"]
        results.append({
            "job_id": j["job_id"],
            "name": j["name"],
            "arrival_time": j["arrival_time"],
            "burst_time": j["burst_time"],
            "start_time": first_start.get(j["job_id"], 0),
            "completion_time": ct,
            "waiting_time": max(0, wt),
            "turnaround_time": tat,
            "priority": j["priority"],
        })

    avg_wt = sum(r["waiting_time"] for r in results) / len(results) if results else 0
    avg_tat = sum(r["turnaround_time"] for r in results) / len(results) if results else 0

    return {
        "algorithm": f"Round Robin (Quantum={quantum})",
        "quantum": quantum,
        "jobs": results,
        "gantt": gantt,
        "avg_waiting_time": round(avg_wt, 2),
        "avg_turnaround_time": round(avg_tat, 2),
    }


def run_priority(jobs: List[dict]) -> dict:
    """
    Non-preemptive Priority Scheduling.
    Lower priority number = higher priority.
    """
    pending = sorted(deepcopy(jobs), key=lambda j: (j["arrival_time"], j["priority"]))
    results = []
    gantt = []
    current_time = 0
    completed_ids = set()

    while len(completed_ids) < len(jobs):
        # Get available jobs
        available = [j for j in pending
                     if j["job_id"] not in completed_ids and j["arrival_time"] <= current_time]

        if not available:
            # Jump to next arrival
            next_arrival = min(
                (j["arrival_time"] for j in pending if j["job_id"] not in completed_ids),
                default=current_time + 1,
            )
            current_time = next_arrival
            continue

        # Pick highest priority (lowest number)
        available.sort(key=lambda j: (j["priority"], j["arrival_time"]))
        job = available[0]

        start_time = current_time
        completion_time = start_time + job["burst_time"]
        waiting_time = start_time - job["arrival_time"]
        turnaround_time = completion_time - job["arrival_time"]

        results.append({
            "job_id": job["job_id"],
            "name": job["name"],
            "arrival_time": job["arrival_time"],
            "burst_time": job["burst_time"],
            "start_time": start_time,
            "completion_time": completion_time,
            "waiting_time": waiting_time,
            "turnaround_time": turnaround_time,
            "priority": job["priority"],
        })

        gantt.append({
            "job_id": job["job_id"],
            "name": job["name"],
            "start": start_time,
            "end": completion_time,
        })

        current_time = completion_time
        completed_ids.add(job["job_id"])

    avg_wt = sum(r["waiting_time"] for r in results) / len(results) if results else 0
    avg_tat = sum(r["turnaround_time"] for r in results) / len(results) if results else 0

    return {
        "algorithm": "Priority Scheduling (Non-preemptive)",
        "quantum": None,
        "jobs": results,
        "gantt": gantt,
        "avg_waiting_time": round(avg_wt, 2),
        "avg_turnaround_time": round(avg_tat, 2),
    }


def run_scheduler_demo(algorithm: str = "fcfs", quantum: int = 2) -> dict:
    """Entry point: generate demo jobs and run the selected algorithm."""
    jobs = generate_demo_jobs()

    if algorithm.lower() == "rr":
        return run_round_robin(jobs, quantum)
    elif algorithm.lower() == "priority":
        return run_priority(jobs)
    else:
        return run_fcfs(jobs)
