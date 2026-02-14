"""ExperimentRunner: run N matches programmatically with pluggable agents."""

import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from neg_env.agents.base import Agent
from neg_env.core.match import MatchStatus
from neg_env.core.runner import apply_action, apply_message, create_match, get_turn_state
from neg_env.games import get_game_spec
from neg_env.games.builtins import ensure_builtins_registered
from neg_env.logging.match_logger import MatchLog, MatchLogger
from neg_env.types import Action, AllowedAction, action_ok


class ExperimentConfig(BaseModel):
    """Configuration for an experiment."""

    game_id: str = Field(..., description="Game to play")
    num_matches: int = Field(default=1, description="Number of matches to run")
    max_turns_per_match: int = Field(
        default=20,
        description=(
            "Maximum number of turns allowed in a single match. "
            "If this many turns occur without a resolution, the match will be aborted. "
            "A turn typically consists of a single agent taking an action."
        )
    )
    max_messages_per_turn: int = Field(
        default=10,
        description=(
            "Maximum number of messages an agent can send during a single turn. "
            "Prevents agents from flooding the environment with excessive communication in one turn."
        )
    )
    max_message_pings: int = Field(
        default=5,
        description="When an agent uses message_only, max reply rounds from the other agent(s) before returning to the current agent.",
    )
    log_directory: Path | None = Field(default=None, description="Directory to save match logs")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
    open_dashboard: bool = Field(default=False, description="Open local dashboard in browser after run")
    dashboard_port: int = Field(default=8765, description="Port for dashboard server")


class MatchResult(BaseModel):
    """Result of a single match."""

    match_id: str
    game_id: str
    agent_ids: list[str]
    outcome: dict[str, Any] | None = None
    status: str = ""
    num_turns: int = 0
    num_messages: int = 0
    duration_seconds: float = 0.0
    log: MatchLog | None = None
    error: str | None = None


class ExperimentResult(BaseModel):
    """Result of running an experiment (N matches)."""

    game_id: str
    num_matches: int
    match_results: list[MatchResult] = Field(default_factory=list)
    total_duration_seconds: float = 0.0

    @property
    def payoff_matrix(self) -> dict[str, list[float]]:
        """agent_id -> list of payoffs across matches."""
        matrix: dict[str, list[float]] = {}
        for mr in self.match_results:
            if mr.outcome and "payoffs" in mr.outcome:
                for p in mr.outcome["payoffs"]:
                    aid = p["agent_id"]
                    matrix.setdefault(aid, []).append(float(p.get("utility", p.get("value", 0))))
        return matrix

    @property
    def mean_payoffs(self) -> dict[str, float]:
        """agent_id -> mean payoff across matches."""
        return {
            aid: sum(vals) / len(vals) if vals else 0.0
            for aid, vals in self.payoff_matrix.items()
        }

    @property
    def completion_rate(self) -> float:
        """Fraction of matches that finished (FINISHED status)."""
        if not self.match_results:
            return 0.0
        finished = sum(1 for mr in self.match_results if mr.status == "finished")
        return finished / len(self.match_results)


class ExperimentRunner:
    """Runs N matches with pluggable agents and collects results."""

    def __init__(self, config: ExperimentConfig) -> None:
        self._config = config

    def run(self, agents: list[Agent]) -> ExperimentResult:
        """Run the experiment: N matches with the given agents."""
        ensure_builtins_registered()

        spec = get_game_spec(self._config.game_id)
        if spec is None:
            raise ValueError(f"Unknown game: {self._config.game_id}")

        min_agents = getattr(spec, "min_agents", 1)
        if len(agents) < min_agents:
            raise ValueError(
                f"Game '{self._config.game_id}' requires at least {min_agents} agents, got {len(agents)}"
            )

        start_time = time.monotonic()
        match_results: list[MatchResult] = []
        dashboard_thread = None
        dashboard_state: dict[str, Any] | None = None

        if self._config.open_dashboard:
            from neg_env.experiment.dashboard import serve_realtime

            dashboard_state = {
                "config": self._config,
                "match_results": [],
                "status": "running",
                "game_id": self._config.game_id,
                "num_matches": self._config.num_matches,
                "total_duration_seconds": 0.0,
            }
            dashboard_thread = serve_realtime(
                dashboard_state,
                port=self._config.dashboard_port,
                open_browser=True,
            )
            port = self._config.dashboard_port
            print(f"\n  Dashboard: http://127.0.0.1:{port}\n")

        for _ in range(self._config.num_matches):
            mr = self._run_single_match(agents, spec, dashboard_state)
            match_results.append(mr)
            if dashboard_state is not None:
                dashboard_state["match_results"].append(mr.model_dump(mode="json"))

        total_duration = time.monotonic() - start_time
        result = ExperimentResult(
            game_id=self._config.game_id,
            num_matches=self._config.num_matches,
            match_results=match_results,
            total_duration_seconds=total_duration,
        )

        if dashboard_state is not None and dashboard_thread is not None:
            dashboard_state["status"] = "finished"
            dashboard_state["total_duration_seconds"] = total_duration
            print(f"  Completion rate: {result.completion_rate:.0%}")
            print(f"  Mean payoffs: {result.mean_payoffs}")
            print(f"  Dashboard at http://127.0.0.1:{self._config.dashboard_port} (Ctrl+C to exit)\n")
            dashboard_thread.join()
        return result

    def _push_live_event(
        self,
        dashboard_state: dict[str, Any] | None,
        event_type: str,
        agent_id: str | None = None,
        **data: Any,
    ) -> None:
        if not dashboard_state:
            return
        current = dashboard_state.get("current_match")
        if not current or "events" not in current:
            return
        current["events"].append({
            "timestamp_ns": time.time_ns(),
            "event_type": event_type,
            "agent_id": agent_id,
            "data": data,
        })

    def _run_single_match(
        self, agents: list[Agent], spec: Any, dashboard_state: dict[str, Any] | None = None
    ) -> MatchResult:
        """Run a single match to completion or max_turns."""
        match_id = uuid.uuid4().hex
        agent_ids = [a.agent_id for a in agents]
        agent_map = {a.agent_id: a for a in agents}
        match = create_match(match_id, self._config.game_id, spec, agent_ids)

        if dashboard_state is not None:
            dashboard_state["current_match"] = {
                "match_id": match_id,
                "agent_ids": agent_ids,
                "events": [],
            }

        logger = MatchLogger(match_id, self._config.game_id, agent_ids)
        logger.set_metadata(**self._config.metadata)
        logger.log_event("match_start")
        self._push_live_event(dashboard_state, "match_start")

        for agent in agents:
            agent.on_match_start(match_id, self._config.game_id, agent_ids)

        start_time = time.monotonic()
        turn_count = 0
        message_count = 0
        error_str: str | None = None

        try:
            while match.status == MatchStatus.RUNNING and turn_count < self._config.max_turns_per_match:
                current_agent_id = agent_ids[match.current_turn_index % len(agent_ids)]
                agent = agent_map[current_agent_id]

                state = get_turn_state(match, current_agent_id)
                if state is None:
                    break

                response = agent.act(state)

                for msg in response.messages[: self._config.max_messages_per_turn]:
                    msg_result = apply_message(
                        match, current_agent_id, msg.scope.value, msg.content, msg.to_agent_ids or None
                    )
                    if msg_result.ok:
                        message_count += 1
                    logger.log_messages(current_agent_id, [msg])
                    self._push_live_event(
                        dashboard_state,
                        "message",
                        agent_id=current_agent_id,
                        scope=msg.scope.value,
                        content=msg.content,
                        to_agent_ids=msg.to_agent_ids or [],
                    )

                action = response.action
                result = apply_action(match, current_agent_id, action)
                logger.log_action(current_agent_id, action.action_type, action.payload, result)
                self._push_live_event(
                    dashboard_state,
                    "action",
                    agent_id=current_agent_id,
                    action_type=action.action_type,
                    payload=action.payload,
                    ok=result.ok,
                    error=result.error,
                    error_detail=result.error_detail,
                )

                message_only_action = AllowedAction(
                    action_type="message_only",
                    description="Only send messages in response to new chat",
                    payload_schema={},
                )
                ping_count = 0
                other_ids = [a for a in agent_ids if a != current_agent_id]
                while (
                    match.status == MatchStatus.RUNNING
                    and action.action_type == "message_only"
                    and ping_count < self._config.max_message_pings
                ):
                    for other_id in other_ids:
                        if match.status != MatchStatus.RUNNING:
                            break
                        state_other = get_turn_state(match, other_id)
                        if state_other is None:
                            continue
                        state_other = state_other.model_copy(
                            update={"allowed_actions": [message_only_action]}
                        )
                        resp = agent_map[other_id].act(state_other)
                        for msg in resp.messages[: self._config.max_messages_per_turn]:
                            msg_result = apply_message(
                                match, other_id, msg.scope.value, msg.content, msg.to_agent_ids or None
                            )
                            if msg_result.ok:
                                message_count += 1
                            logger.log_messages(other_id, [msg])
                            self._push_live_event(
                                dashboard_state,
                                "message",
                                agent_id=other_id,
                                scope=msg.scope.value,
                                content=msg.content,
                                to_agent_ids=msg.to_agent_ids or [],
                            )
                        act_other = resp.action
                        if act_other.action_type != "message_only":
                            act_other = Action(action_type="message_only", payload={})
                        apply_action(match, other_id, act_other)
                        logger.log_action(
                            other_id, act_other.action_type, act_other.payload, action_ok()
                        )
                        self._push_live_event(
                            dashboard_state,
                            "action",
                            agent_id=other_id,
                            action_type=act_other.action_type,
                            payload=act_other.payload,
                            ok=True,
                            error=None,
                            error_detail=None,
                        )
                    ping_count += 1
                    state = get_turn_state(match, current_agent_id)
                    if state is None:
                        break
                    response = agent.act(state)
                    for msg in response.messages[: self._config.max_messages_per_turn]:
                        msg_result = apply_message(
                            match, current_agent_id, msg.scope.value, msg.content, msg.to_agent_ids or None
                        )
                        if msg_result.ok:
                            message_count += 1
                        logger.log_messages(current_agent_id, [msg])
                        self._push_live_event(
                            dashboard_state,
                            "message",
                            agent_id=current_agent_id,
                            scope=msg.scope.value,
                            content=msg.content,
                            to_agent_ids=msg.to_agent_ids or [],
                        )
                    action = response.action
                    result = apply_action(match, current_agent_id, action)
                    logger.log_action(current_agent_id, action.action_type, action.payload, result)
                    self._push_live_event(
                        dashboard_state,
                        "action",
                        agent_id=current_agent_id,
                        action_type=action.action_type,
                        payload=action.payload,
                        ok=result.ok,
                        error=result.error,
                        error_detail=result.error_detail,
                    )
                    if action.action_type != "message_only":
                        break

                if action.action_type not in ("pass", "message_only"):
                    turn_count += 1
        except Exception as e:
            error_str = str(e)

        duration = time.monotonic() - start_time
        logger.set_outcome(match.outcome)
        logger.log_event("match_end", status=match.status.value)
        self._push_live_event(dashboard_state, "match_end", status=match.status.value)
        if dashboard_state is not None:
            dashboard_state["current_match"] = None

        for agent in agents:
            agent.on_match_end(match_id, match.outcome)

        log = logger.to_log()
        if self._config.log_directory:
            logger.save(self._config.log_directory)

        return MatchResult(
            match_id=match_id,
            game_id=self._config.game_id,
            agent_ids=agent_ids,
            outcome=match.outcome,
            status=match.status.value,
            num_turns=turn_count,
            num_messages=message_count,
            duration_seconds=duration,
            log=log,
            error=error_str,
        )
