import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest
import pytest_asyncio

from src.scheduler.executor import WorkflowExecutor
from src.scheduler.loop import ExecutionLoop
from src.scheduler.queue import TaskQueue
from src.scheduler.task import Task, TaskType
from src.scheduler.task_request import TaskRequest


pytestmark = pytest.mark.asyncio


@dataclass
class RecordingWorkflowExecutor(WorkflowExecutor):
    start_log: List[str]
    end_log: List[str]
    currently_running_count: int
    max_currently_running_count: int
    started_events: Dict[str, asyncio.Event]
    release_events: Dict[str, asyncio.Event]
    finished_events: Dict[str, asyncio.Event]

    def __init__(self):
        super().__init__()
        self.start_log = []
        self.end_log = []
        self.currently_running_count = 0
        self.max_currently_running_count = 0
        self.started_events = {}
        self.release_events = {}
        self.finished_events = {}

    def started_event_for(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self.started_events[task_id] = event
        return event

    def release_event_for(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self.release_events[task_id] = event
        return event

    def finished_event_for(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self.finished_events[task_id] = event
        return event

    async def execute(self, task: Task) -> Dict[str, Any]:
        self.start_log.append(task.id)
        self.currently_running_count += 1
        self.max_currently_running_count = max(
            self.max_currently_running_count, self.currently_running_count
        )
        if task.id in self.started_events:
            self.started_events[task.id].set()

        release_event = self.release_events.get(task.id)
        if release_event is not None:
            await release_event.wait()

        self.end_log.append(task.id)
        self.currently_running_count -= 1
        finished_event = self.finished_events.get(task.id)
        if finished_event is not None:
            finished_event.set()
        return {"task_id": task.id, "type": task.type}


@pytest_asyncio.fixture
async def task_queue() -> TaskQueue:
    return TaskQueue()


@pytest_asyncio.fixture
async def workflow_executor() -> RecordingWorkflowExecutor:
    return RecordingWorkflowExecutor()


@pytest_asyncio.fixture
async def execution_loop(task_queue: TaskQueue, workflow_executor: RecordingWorkflowExecutor) -> ExecutionLoop:
    return ExecutionLoop(queue=task_queue, executor=workflow_executor)


def make_task(task_id: str, task_type: TaskType) -> Task:
    return Task(
        id=task_id,
        type=task_type,
        request=TaskRequest(task="", repo_path=""),
        created_at=0.0,
    )


async def test_active_tasks_execute_strictly_in_submission_order(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    workflow_executor: RecordingWorkflowExecutor,
):
    tasks = [make_task(str(index), "active") for index in range(3)]
    for task in tasks:
        workflow_executor.started_event_for(task.id)
        workflow_executor.release_event_for(task.id)
        workflow_executor.finished_event_for(task.id)

    await execution_loop.start()
    try:
        await asyncio.gather(*(task_queue.enqueue(task) for task in tasks))

        for task in tasks:
            await workflow_executor.started_events[task.id].wait()
            assert workflow_executor.start_log == [queued.id for queued in tasks[: tasks.index(task) + 1]]
            workflow_executor.release_events[task.id].set()
            await workflow_executor.finished_events[task.id].wait()

        assert workflow_executor.end_log == [task.id for task in tasks]
    finally:
        await execution_loop.stop()


async def test_mutation_exclusivity_never_exceeds_one_active_task(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    workflow_executor: RecordingWorkflowExecutor,
):
    tasks = [make_task(str(index), "active") for index in range(2)]
    for task in tasks:
        workflow_executor.started_event_for(task.id)
        workflow_executor.release_event_for(task.id)
        workflow_executor.finished_event_for(task.id)

    await execution_loop.start()
    try:
        await asyncio.gather(*(task_queue.enqueue(task) for task in tasks))

        await workflow_executor.started_events[tasks[0].id].wait()
        assert workflow_executor.currently_running_count == 1
        assert not workflow_executor.started_events[tasks[1].id].is_set()

        workflow_executor.release_events[tasks[0].id].set()
        await workflow_executor.finished_events[tasks[0].id].wait()
        await workflow_executor.started_events[tasks[1].id].wait()
        assert workflow_executor.currently_running_count == 1

        workflow_executor.release_events[tasks[1].id].set()
        await workflow_executor.finished_events[tasks[1].id].wait()
        assert workflow_executor.end_log == [task.id for task in tasks]
        assert workflow_executor.max_currently_running_count == 1
    finally:
        await execution_loop.stop()


async def test_concurrent_submissions_do_not_drop_or_duplicate_tasks(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    workflow_executor: RecordingWorkflowExecutor,
):
    tasks = [make_task(str(index), "active") for index in range(20)]
    for task in tasks:
        workflow_executor.started_event_for(task.id)
        workflow_executor.release_event_for(task.id)
        workflow_executor.finished_event_for(task.id)

    await execution_loop.start()
    try:
        async def submit_subset(subset: List[Task]) -> None:
            await asyncio.gather(*(task_queue.enqueue(task) for task in subset))

        batches = [tasks[index : index + 5] for index in range(0, len(tasks), 5)]
        await asyncio.gather(*(submit_subset(batch) for batch in batches))

        for task in tasks:
            await workflow_executor.started_events[task.id].wait()
            workflow_executor.release_events[task.id].set()
            await workflow_executor.finished_events[task.id].wait()

        assert workflow_executor.start_log == [task.id for task in tasks]
        assert workflow_executor.end_log == [task.id for task in tasks]
    finally:
        await execution_loop.stop()


async def test_submit_task_starts_the_loop_and_preserves_fifo_order(
    execution_loop: ExecutionLoop,
    workflow_executor: RecordingWorkflowExecutor,
):
    tasks = [make_task(str(index), "active") for index in range(3)]
    for task in tasks:
        workflow_executor.started_event_for(task.id)
        workflow_executor.release_event_for(task.id)
        workflow_executor.finished_event_for(task.id)

    try:
        await asyncio.gather(*(execution_loop.submit_task(task) for task in tasks))

        for task in tasks:
            await workflow_executor.started_events[task.id].wait()
            workflow_executor.release_events[task.id].set()
            await workflow_executor.finished_events[task.id].wait()

        assert workflow_executor.start_log == [task.id for task in tasks]
        assert workflow_executor.end_log == [task.id for task in tasks]
    finally:
        await execution_loop.stop()


async def test_passive_tasks_do_not_block_active_tasks(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    workflow_executor: RecordingWorkflowExecutor,
):
    passive = make_task("passive-1", "passive")
    active = make_task("active-1", "active")

    workflow_executor.started_event_for(passive.id)
    workflow_executor.release_event_for(passive.id)
    workflow_executor.finished_event_for(passive.id)
    workflow_executor.started_event_for(active.id)
    workflow_executor.release_event_for(active.id)
    workflow_executor.finished_event_for(active.id)

    await execution_loop.start()
    try:
        await task_queue.enqueue(passive)
        await workflow_executor.started_events[passive.id].wait()

        await task_queue.enqueue(active)
        await workflow_executor.started_events[active.id].wait()

        assert workflow_executor.start_log == [passive.id, active.id]
        assert workflow_executor.currently_running_count == 2
        assert not workflow_executor.finished_events[passive.id].is_set()

        workflow_executor.release_events[active.id].set()
        workflow_executor.release_events[passive.id].set()
        await workflow_executor.finished_events[active.id].wait()
        await workflow_executor.finished_events[passive.id].wait()

        assert workflow_executor.start_log == [passive.id, active.id]
        assert workflow_executor.max_currently_running_count >= 2
    finally:
        await execution_loop.stop()
