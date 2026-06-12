import asyncio
from dataclasses import dataclass
from typing import Dict, List

import pytest
import pytest_asyncio

from src.scheduler.dispatcher import TaskDispatcher
from src.scheduler.loop import ExecutionLoop
from src.scheduler.queue import TaskQueue
from src.scheduler.task import PipelineTask, QueryTask, Task


pytestmark = pytest.mark.asyncio


@dataclass
class RecordingTaskDispatcher(TaskDispatcher):
    start_log: List[str]
    end_log: List[str]
    currently_running_count: int
    max_currently_running_count: int
    started_events: Dict[str, asyncio.Event]
    release_events: Dict[str, asyncio.Event]
    finished_events: Dict[str, asyncio.Event]

    def __init__(self):
        # Skip TaskDispatcher.__init__ — no real pipeline config needed for tests.
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

    async def execute(self, task: Task) -> None:
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


@pytest_asyncio.fixture
async def task_queue() -> TaskQueue:
    return TaskQueue()


@pytest_asyncio.fixture
async def task_dispatcher() -> RecordingTaskDispatcher:
    return RecordingTaskDispatcher()


@pytest_asyncio.fixture
async def execution_loop(task_queue: TaskQueue, task_dispatcher: RecordingTaskDispatcher) -> ExecutionLoop:
    return ExecutionLoop(queue=task_queue, executor=task_dispatcher)


def make_task(task_id: str, task_type: str) -> Task:
    if task_type == "active":
        return PipelineTask(id=task_id, repo="test")
    return QueryTask(id=task_id, query_text="", response_url="", repo="test")


async def test_active_tasks_execute_strictly_in_submission_order(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    task_dispatcher: RecordingTaskDispatcher,
):
    tasks = [make_task(str(index), "active") for index in range(3)]
    for task in tasks:
        task_dispatcher.started_event_for(task.id)
        task_dispatcher.release_event_for(task.id)
        task_dispatcher.finished_event_for(task.id)

    await execution_loop.start()
    try:
        await asyncio.gather(*(task_queue.enqueue(task) for task in tasks))

        for task in tasks:
            await task_dispatcher.started_events[task.id].wait()
            assert task_dispatcher.start_log == [queued.id for queued in tasks[: tasks.index(task) + 1]]
            task_dispatcher.release_events[task.id].set()
            await task_dispatcher.finished_events[task.id].wait()

        assert task_dispatcher.end_log == [task.id for task in tasks]
    finally:
        await execution_loop.stop()


async def test_mutation_exclusivity_never_exceeds_one_active_task(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    task_dispatcher: RecordingTaskDispatcher,
):
    tasks = [make_task(str(index), "active") for index in range(2)]
    for task in tasks:
        task_dispatcher.started_event_for(task.id)
        task_dispatcher.release_event_for(task.id)
        task_dispatcher.finished_event_for(task.id)

    await execution_loop.start()
    try:
        await asyncio.gather(*(task_queue.enqueue(task) for task in tasks))

        await task_dispatcher.started_events[tasks[0].id].wait()
        assert task_dispatcher.currently_running_count == 1
        assert not task_dispatcher.started_events[tasks[1].id].is_set()

        task_dispatcher.release_events[tasks[0].id].set()
        await task_dispatcher.finished_events[tasks[0].id].wait()
        await task_dispatcher.started_events[tasks[1].id].wait()
        assert task_dispatcher.currently_running_count == 1

        task_dispatcher.release_events[tasks[1].id].set()
        await task_dispatcher.finished_events[tasks[1].id].wait()
        assert task_dispatcher.end_log == [task.id for task in tasks]
        assert task_dispatcher.max_currently_running_count == 1
    finally:
        await execution_loop.stop()


async def test_concurrent_submissions_do_not_drop_or_duplicate_tasks(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    task_dispatcher: RecordingTaskDispatcher,
):
    tasks = [make_task(str(index), "active") for index in range(20)]
    for task in tasks:
        task_dispatcher.started_event_for(task.id)
        task_dispatcher.release_event_for(task.id)
        task_dispatcher.finished_event_for(task.id)

    await execution_loop.start()
    try:
        async def submit_subset(subset: List[Task]) -> None:
            await asyncio.gather(*(task_queue.enqueue(task) for task in subset))

        batches = [tasks[index : index + 5] for index in range(0, len(tasks), 5)]
        await asyncio.gather(*(submit_subset(batch) for batch in batches))

        for task in tasks:
            await task_dispatcher.started_events[task.id].wait()
            task_dispatcher.release_events[task.id].set()
            await task_dispatcher.finished_events[task.id].wait()

        assert task_dispatcher.start_log == [task.id for task in tasks]
        assert task_dispatcher.end_log == [task.id for task in tasks]
    finally:
        await execution_loop.stop()


async def test_submit_task_starts_the_loop_and_preserves_fifo_order(
    execution_loop: ExecutionLoop,
    task_dispatcher: RecordingTaskDispatcher,
):
    tasks = [make_task(str(index), "active") for index in range(3)]
    for task in tasks:
        task_dispatcher.started_event_for(task.id)
        task_dispatcher.release_event_for(task.id)
        task_dispatcher.finished_event_for(task.id)

    try:
        await asyncio.gather(*(execution_loop.submit_task(task) for task in tasks))

        for task in tasks:
            await task_dispatcher.started_events[task.id].wait()
            task_dispatcher.release_events[task.id].set()
            await task_dispatcher.finished_events[task.id].wait()

        assert task_dispatcher.start_log == [task.id for task in tasks]
        assert task_dispatcher.end_log == [task.id for task in tasks]
    finally:
        await execution_loop.stop()


async def test_passive_tasks_do_not_block_active_tasks(
    execution_loop: ExecutionLoop,
    task_queue: TaskQueue,
    task_dispatcher: RecordingTaskDispatcher,
):
    passive = make_task("passive-1", "passive")
    active = make_task("active-1", "active")

    task_dispatcher.started_event_for(passive.id)
    task_dispatcher.release_event_for(passive.id)
    task_dispatcher.finished_event_for(passive.id)
    task_dispatcher.started_event_for(active.id)
    task_dispatcher.release_event_for(active.id)
    task_dispatcher.finished_event_for(active.id)

    await execution_loop.start()
    try:
        await task_queue.enqueue(passive)
        await task_dispatcher.started_events[passive.id].wait()

        await task_queue.enqueue(active)
        await task_dispatcher.started_events[active.id].wait()

        assert task_dispatcher.start_log == [passive.id, active.id]
        assert task_dispatcher.currently_running_count == 2
        assert not task_dispatcher.finished_events[passive.id].is_set()

        task_dispatcher.release_events[active.id].set()
        task_dispatcher.release_events[passive.id].set()
        await task_dispatcher.finished_events[active.id].wait()
        await task_dispatcher.finished_events[passive.id].wait()

        assert task_dispatcher.start_log == [passive.id, active.id]
        assert task_dispatcher.max_currently_running_count >= 2
    finally:
        await execution_loop.stop()
