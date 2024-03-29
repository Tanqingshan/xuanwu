from typing import Any, Dict, Union, Optional, Tuple

try:
    from brax.envs import Env, Wrapper
except ImportError:
    raise ImportError("You need to install `brax` to use the brax wrapper.")
import jax
import jax.numpy as jnp
import chex
from gymnax.environments.environment import Environment, EnvState, EnvParams
from flax import struct

import math



@struct.dataclass
class State:
    """A duck-type State of brax"""

    pipeline_state: chex.ArrayTree
    obs: jax.Array
    reward: jax.Array
    done: jax.Array
    metrics: Dict[str, jax.Array] = struct.field(default_factory=dict)
    info: Dict[str, Any] = struct.field(default_factory=dict)


class GymnaxToBraxWrapper(Env):
    def __init__(self, env: Environment, env_params: Optional[EnvParams] = None):
        """Wrap Gymnax environment as Brax environment

        Primarily useful for including obs, reward, and done as part of state.
        Compatible with all brax wrappers, but AutoResetWrapper is redundant since Gymnax environments
        already reset state.

        Args:
            env: Gymnax environment instance
        """
        self.env = env
        self.env_params = env_params or env.default_params

    def reset(self, rng: chex.PRNGKey) -> State:
        """Reset, return brax State. Save rng and params in info field for step"""
        rng, reset_rng = jax.random.split(rng)
        obs, env_state = self.env.reset(reset_rng, self.env_params)
        return State(
            env_state,
            obs,
            jnp.zeros(()),
            jnp.zeros(()),
            metrics={},
            info={
                "_rng": rng,
                "_env_params": self.env_params,
                "discount": jnp.ones(())
            },
        )

    def step(
        self,
        state: State,
        action: Union[chex.Scalar, chex.Array]
    ) -> State:
        """Step, return brax State. Update stored rng and params (if provided) in info field"""
        state_info = state.info
        rng, step_rng = jax.random.split(state_info["_rng"])

        # call step_env() instead of step() to disable autoreset
        o, pipeline_state, r, d, info = self.env.step_env(
            step_rng, state.pipeline_state, action, state_info["_env_params"])
        
        d = d.astype(jnp.float32)

        state.info.update(_rng=rng)
        state_info.update(info)

        return state.replace(pipeline_state=pipeline_state, obs=o, reward=r, done=d, info=state_info)

    def action_size(self) -> int:
        a_space = self.env.action_space(self.env_params)
        action_shape = jax.eval_shape(a_space.sample, jax.random.PRNGKey(0))
        return math.prod(action_shape)

    def observation_size(self) -> int:
        o_space = self.env.observation_space(self.env_params)
        obs_shape = jax.eval_shape(o_space.sample, jax.random.PRNGKey(0))
        return math.prod(obs_shape)

    def backend(self) -> str:
        return "gymnax"
