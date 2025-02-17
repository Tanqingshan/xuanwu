import jax

from omegaconf import DictConfig, OmegaConf
import hydra
import logging

from evorl.utils.cfg_utils import get_output_dir
from evorl.recorders import WandbRecorder, LogRecorder, ChainRecorder
from pathlib import Path

logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="../configs", config_name="config")
def train(config: DictConfig) -> None:
    logger.info("config:\n"+OmegaConf.to_yaml(config))

    if config.debug:
        from jax import config as jax_config
        jax_config.update("jax_debug_nans", True)
        # jax_config.update("jax_debug_infs", True)

    workflow_cls = hydra.utils.get_class(config.workflow_cls)

    devices = jax.local_devices()
    if len(devices) > 1:
        logger.info(f"Enable Multi Devices: {devices}")
        workflow = workflow_cls.build_from_config(
            config, enable_multi_devices=True, devices=devices,
        )
    else:
        workflow = workflow_cls.build_from_config(
            config,
            enable_jit=True
        )

    output_dir = get_output_dir()
    wandb_project = config.wandb.project
    wandb_tags = [workflow_cls.name(), config.env.env_name, config.env.env_type] + \
        OmegaConf.to_container(config.wandb.tags)
    wandb_name = '-'.join(
        [workflow_cls.name(), config.env.env_name, config.env.env_type]
    )
    wandb_mode = 'online' if config.wandb.enable and not config.debug else 'disabled'

    wandb_recorder = WandbRecorder(
        project=wandb_project,
        name=wandb_name,
        config=OmegaConf.to_container(config),  # save the unrescaled config
        tags=wandb_tags,
        dir=output_dir,
        mode=wandb_mode
    )
    log_recorder = LogRecorder(log_path=output_dir/f'{wandb_name}.log')
    workflow.add_recorders([wandb_recorder, log_recorder])

    state = workflow.init(jax.random.PRNGKey(config.seed))
    state = workflow.learn(state)

    workflow.close()


if __name__ == "__main__":
    train()
