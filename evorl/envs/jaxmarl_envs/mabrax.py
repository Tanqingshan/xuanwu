from typing import Dict, Literal, Optional, Tuple
import chex
from jaxmarl.environments.multi_agent_env import MultiAgentEnv
from gymnax.environments import spaces
from brax import envs
import jax
import jax.numpy as jnp
from functools import partial

from jaxmarl.environments.mabrax.mabrax_env import (
    MABraxEnv, _agent_action_mapping, _agent_observation_mapping
)

# TODO: move homogenisation to a separate wrapper


class MABraxEnvV2(MABraxEnv):
    def __init__(
        self,
        env_name: str,
        homogenisation_method: Optional[Literal["max", "concat"]] = None,
        backend: str = "positional",
        **kwargs
    ):
        """Multi-Agent Brax environment.

        Args:
            env_name: Name of the environment to be used.
            episode_length: Length of an episode. Defaults to 1000.
            action_repeat: How many repeated actions to take per environment
                step. Defaults to 1.
            auto_reset: Whether to automatically reset the environment when
                an episode ends. Defaults to True.
            homogenisation_method: Method to homogenise observations and actions
                across agents. If None, no homogenisation is performed, and
                observations and actions are returned as is. If "max", observations
                and actions are homogenised by taking the maximum dimension across
                all agents and zero-padding the rest. In this case, the index of the
                agent is prepended to the observation as a one-hot vector. If "concat",
                observations and actions are homogenised by masking the dimensions of
                the other agents with zeros in the full observation and action vectors.
                Defaults to None.
        """
        base_env_name = env_name.split("_")[0]
        env = envs.get_environment(base_env_name, backend=backend, **kwargs)

        self.env = env
        self.homogenisation_method = homogenisation_method
        self.agent_obs_mapping = _agent_observation_mapping[env_name]
        self.agent_action_mapping = _agent_action_mapping[env_name]
        self.agents = list(self.agent_obs_mapping.keys())

        self.num_agents = len(self.agent_obs_mapping)
        obs_sizes = {
            agent: self.num_agents
            + max([o.size for o in self.agent_obs_mapping.values()])
            if homogenisation_method == "max"
            else self.env.observation_size
            if homogenisation_method == "concat"
            else obs.size
            for agent, obs in self.agent_obs_mapping.items()
        }
        act_sizes = {
            agent: max([a.size for a in self.agent_action_mapping.values()])
            if homogenisation_method == "max"
            else self.env.action_size
            if homogenisation_method == "concat"
            else act.size
            for agent, act in self.agent_action_mapping.items()
        }

        self.observation_spaces = {
            agent: spaces.Box(
                -jnp.inf,
                jnp.inf,
                shape=(obs_sizes[agent],),
            )
            for agent in self.agents
        }
        self.action_spaces = {
            agent: spaces.Box(
                -1.0,
                1.0,
                shape=(act_sizes[agent],),
            )
            for agent in self.agents
        }


class Ant(MABraxEnvV2):
    def __init__(self, **kwargs):
        super().__init__("ant_4x2", **kwargs)


class HalfCheetah(MABraxEnvV2):
    def __init__(self, **kwargs):
        super().__init__("halfcheetah_6x1", **kwargs)


class Hopper(MABraxEnvV2):
    def __init__(self, **kwargs):
        super().__init__("hopper_3x1", **kwargs)


class Humanoid(MABraxEnvV2):
    def __init__(self, **kwargs):
        super().__init__("humanoid_9|8", **kwargs)


class Walker2d(MABraxEnvV2):
    def __init__(self, **kwargs):
        super().__init__("walker2d_2x3", **kwargs)


def make_mabrax_env(env_id: str, **env_kwargs):
    if env_id == "ant_4x2":
        env = Ant(**env_kwargs)
    elif env_id == "halfcheetah_6x1":
        env = HalfCheetah(**env_kwargs)
    elif env_id == "hopper_3x1":
        env = Hopper(**env_kwargs)
    elif env_id == "humanoid_9|8":
        env = Humanoid(**env_kwargs)
    elif env_id == "walker2d_2x3":
        env = Walker2d(**env_kwargs)

    return env