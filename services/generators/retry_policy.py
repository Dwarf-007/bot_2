from __future__ import annotations
import random, time
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Optional, TypeVar
T=TypeVar('T')
@dataclass(frozen=True)
class RetryPolicy:
    max_attempts:int=3; initial_delay_seconds:float=2.0; backoff_factor:float=2.0; max_delay_seconds:float=30.0; jitter_seconds:float=0.5
    def to_dict(self): return asdict(self)
    def delay_for_attempt(self, attempt_index:int)->float:
        base=min(self.initial_delay_seconds*(self.backoff_factor**max(0,attempt_index-1)), self.max_delay_seconds)
        if self.jitter_seconds>0: base += random.uniform(0,self.jitter_seconds)
        return max(0.0, base)
@dataclass(frozen=True)
class RetryAttempt:
    attempt:int; success:bool; error_type:str=''; error_message:str=''; delay_seconds:float=0.0
    def to_dict(self): return asdict(self)
class RetryExecutor:
    def __init__(self, policy:Optional[RetryPolicy]=None, sleep_func:Callable[[float],None]=time.sleep):
        self.policy=policy or RetryPolicy(); self.sleep_func=sleep_func; self.attempts=[]
    def run(self, operation:Callable[[],T], retry_on:Iterable[type[BaseException]]=(Exception,))->T:
        last=None
        for attempt in range(1, max(1,self.policy.max_attempts)+1):
            try:
                res=operation(); self.attempts.append(RetryAttempt(attempt, True)); return res
            except tuple(retry_on) as exc:
                last=exc; is_last=attempt>=self.policy.max_attempts; delay=0 if is_last else self.policy.delay_for_attempt(attempt)
                self.attempts.append(RetryAttempt(attempt, False, type(exc).__name__, str(exc), delay))
                if is_last: break
                self.sleep_func(delay)
        raise last
    def attempts_as_dicts(self): return [a.to_dict() for a in self.attempts]
