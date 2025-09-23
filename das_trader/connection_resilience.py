"""Enhanced connection resilience features for DAS Trader API."""

import asyncio
import logging
import random
import time
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .enhanced_exceptions import (
    DASConnectionError, DASTimeoutError, DASAuthenticationError,
    DASRecoverableError, DASRateLimitError
)

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionAttempt:
    """Track connection attempt details."""
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    duration: Optional[float] = None
    attempt_number: int = 0


@dataclass
class ConnectionHealth:
    """Track connection health metrics."""
    last_successful_command: datetime = field(default_factory=datetime.now)
    consecutive_failures: int = 0
    total_reconnects: int = 0
    uptime_start: Optional[datetime] = None
    recent_attempts: List[ConnectionAttempt] = field(default_factory=list)

    def add_attempt(self, attempt: ConnectionAttempt):
        """Add connection attempt to history."""
        self.recent_attempts.append(attempt)
        # Keep only last 10 attempts
        if len(self.recent_attempts) > 10:
            self.recent_attempts.pop(0)

    def mark_success(self):
        """Mark successful operation."""
        self.last_successful_command = datetime.now()
        self.consecutive_failures = 0
        if self.uptime_start is None:
            self.uptime_start = datetime.now()

    def mark_failure(self):
        """Mark failed operation."""
        self.consecutive_failures += 1

    def get_uptime(self) -> Optional[timedelta]:
        """Get connection uptime."""
        if self.uptime_start:
            return datetime.now() - self.uptime_start
        return None

    def get_success_rate(self) -> float:
        """Get recent success rate."""
        if not self.recent_attempts:
            return 1.0

        successful = sum(1 for attempt in self.recent_attempts if attempt.success)
        return successful / len(self.recent_attempts)


class ExponentialBackoff:
    """Exponential backoff with jitter for reconnection attempts."""

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt_count = 0

    def get_delay(self) -> float:
        """Get next delay duration."""
        delay = min(
            self.base_delay * (self.multiplier ** self.attempt_count),
            self.max_delay
        )

        if self.jitter:
            # Add random jitter (±25% of delay)
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)

        self.attempt_count += 1
        return max(0.1, delay)  # Minimum 100ms delay

    def reset(self):
        """Reset backoff counter."""
        self.attempt_count = 0


class CircuitBreaker:
    """Circuit breaker pattern for connection management."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise DASConnectionError(
                    "Circuit breaker is open",
                    retry_after=self.recovery_timeout
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout

    def _on_success(self):
        """Handle successful operation."""
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class ConnectionResilientManager:
    """Enhanced connection manager with resilience features."""

    def __init__(
        self,
        connection_manager,
        max_reconnect_attempts: int = 10,
        health_check_interval: float = 30.0,
        command_timeout: float = 10.0
    ):
        self.connection_manager = connection_manager
        self.max_reconnect_attempts = max_reconnect_attempts
        self.health_check_interval = health_check_interval
        self.command_timeout = command_timeout

        # State tracking
        self.state = ConnectionState.DISCONNECTED
        self.health = ConnectionHealth()
        self.backoff = ExponentialBackoff()
        self.circuit_breaker = CircuitBreaker()

        # Async tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        # Credentials for reconnection
        self._credentials: Optional[Dict[str, str]] = None

        # Event callbacks
        self._state_change_callbacks: List[Callable] = []
        self._health_callbacks: List[Callable] = []

    async def connect(self, username: str, password: str, account: str):
        """Enhanced connect with resilience."""
        self._credentials = {
            "username": username,
            "password": password,
            "account": account
        }

        await self._attempt_connection()

        # Start health monitoring
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _attempt_connection(self) -> bool:
        """Attempt connection with tracking."""
        if not self._credentials:
            raise DASAuthenticationError("No credentials available for connection")

        attempt_start = time.time()
        attempt = ConnectionAttempt(
            timestamp=datetime.now(),
            success=False,
            attempt_number=len(self.health.recent_attempts) + 1
        )

        try:
            self.state = ConnectionState.CONNECTING
            await self._notify_state_change()

            # Use circuit breaker for connection attempt
            await self.circuit_breaker.call(
                self.connection_manager.connect,
                self._credentials["username"],
                self._credentials["password"],
                self._credentials["account"]
            )

            attempt.success = True
            attempt.duration = time.time() - attempt_start
            self.health.add_attempt(attempt)
            self.health.mark_success()

            self.state = ConnectionState.AUTHENTICATED
            self.backoff.reset()

            await self._notify_state_change()
            logger.info("✅ DAS connection established successfully")
            return True

        except Exception as e:
            attempt.success = False
            attempt.error = str(e)
            attempt.duration = time.time() - attempt_start
            self.health.add_attempt(attempt)
            self.health.mark_failure()

            self.state = ConnectionState.FAILED
            await self._notify_state_change()

            logger.error(f"❌ Connection attempt failed: {e}")
            raise

    async def send_command_resilient(
        self,
        command: str,
        wait_response: bool = False,
        response_type: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """Send command with resilience and retry logic."""
        if not self.is_healthy():
            if self.state != ConnectionState.RECONNECTING:
                asyncio.create_task(self._reconnect())
            raise DASConnectionError("Connection not healthy")

        timeout = timeout or self.command_timeout
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Use circuit breaker for command execution
                result = await self.circuit_breaker.call(
                    self._execute_command_with_timeout,
                    command, wait_response, response_type, timeout
                )

                self.health.mark_success()
                return result

            except DASTimeoutError as e:
                self.health.mark_failure()
                if attempt < max_retries - 1:
                    logger.warning(f"Command timeout (attempt {attempt + 1}/{max_retries}), retrying...")
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                raise

            except DASRateLimitError as e:
                if e.retry_after:
                    logger.warning(f"Rate limited, waiting {e.retry_after}s before retry")
                    await asyncio.sleep(e.retry_after)
                    continue
                raise

            except DASRecoverableError as e:
                self.health.mark_failure()
                if attempt < max_retries - 1:
                    logger.warning(f"Recoverable error (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise

            except Exception as e:
                self.health.mark_failure()
                # Check if this might trigger reconnection
                if self.health.consecutive_failures >= 3:
                    asyncio.create_task(self._reconnect())
                raise

        raise DASConnectionError(f"Command failed after {max_retries} attempts")

    async def _execute_command_with_timeout(
        self,
        command: str,
        wait_response: bool,
        response_type: Optional[str],
        timeout: float
    ):
        """Execute command with timeout."""
        try:
            return await asyncio.wait_for(
                self.connection_manager.send_command(command, wait_response, response_type),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise DASTimeoutError(
                f"Command '{command}' timed out after {timeout}s",
                timeout_duration=timeout,
                operation=command
            )

    async def _health_check_loop(self):
        """Periodic health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                if self.state == ConnectionState.AUTHENTICATED:
                    await self._perform_health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _perform_health_check(self):
        """Perform health check using lightweight command."""
        try:
            # Use a lightweight command for health check
            await asyncio.wait_for(
                self.connection_manager.send_command("PING", wait_response=False),
                timeout=5.0
            )

            self.health.mark_success()

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self.health.mark_failure()

            # If too many consecutive failures, trigger reconnection
            if self.health.consecutive_failures >= 3:
                asyncio.create_task(self._reconnect())

    async def _reconnect(self):
        """Reconnect with exponential backoff."""
        if self.state == ConnectionState.RECONNECTING:
            return  # Already reconnecting

        if self._reconnect_task and not self._reconnect_task.done():
            return  # Reconnection already in progress

        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """Reconnection loop with backoff."""
        self.state = ConnectionState.RECONNECTING
        await self._notify_state_change()

        attempt_count = 0

        while attempt_count < self.max_reconnect_attempts:
            attempt_count += 1
            self.health.total_reconnects += 1

            try:
                logger.info(f"🔄 Reconnection attempt {attempt_count}/{self.max_reconnect_attempts}")

                # Close existing connection
                try:
                    await self.connection_manager.disconnect()
                except Exception:
                    pass

                # Wait with exponential backoff
                delay = self.backoff.get_delay()
                logger.info(f"⏱️ Waiting {delay:.1f}s before reconnect attempt...")
                await asyncio.sleep(delay)

                # Attempt reconnection
                await self._attempt_connection()

                logger.info("✅ Reconnection successful")
                return

            except DASAuthenticationError as e:
                logger.error(f"❌ Authentication failed during reconnect: {e}")
                self.state = ConnectionState.FAILED
                await self._notify_state_change()
                break

            except Exception as e:
                logger.warning(f"⚠️ Reconnection attempt {attempt_count} failed: {e}")

                if attempt_count >= self.max_reconnect_attempts:
                    logger.error("❌ Max reconnection attempts reached")
                    self.state = ConnectionState.FAILED
                    await self._notify_state_change()
                    break

    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        if self.state != ConnectionState.AUTHENTICATED:
            return False

        # Check consecutive failures
        if self.health.consecutive_failures >= 5:
            return False

        # Check last successful command timing
        time_since_success = datetime.now() - self.health.last_successful_command
        if time_since_success.total_seconds() > 300:  # 5 minutes
            return False

        return True

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "state": self.state.value,
            "uptime": str(self.health.get_uptime()) if self.health.get_uptime() else None,
            "success_rate": self.health.get_success_rate(),
            "consecutive_failures": self.health.consecutive_failures,
            "total_reconnects": self.health.total_reconnects,
            "circuit_breaker_state": self.circuit_breaker.state,
            "last_successful_command": self.health.last_successful_command.isoformat(),
            "recent_attempts": len(self.health.recent_attempts)
        }

    def add_state_change_callback(self, callback: Callable):
        """Add callback for state changes."""
        self._state_change_callbacks.append(callback)

    def add_health_callback(self, callback: Callable):
        """Add callback for health updates."""
        self._health_callbacks.append(callback)

    async def _notify_state_change(self):
        """Notify state change callbacks."""
        for callback in self._state_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.state)
                else:
                    callback(self.state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass