from collections import OrderedDict
import numpy as np
from gym.spaces import Dict, Box
from multiworld.core.multitask_env import MultitaskEnv
from multiworld.core.serializable import Serializable
from multiworld.envs.env_util import get_stat_in_paths, create_stats_ordered_dict, get_asset_full_path
from multiworld.envs.mujoco.mujoco_env import MujocoEnv

class HopperVelocityMotorFailureEnv(MujocoEnv, MultitaskEnv, Serializable):
    def __init__(self, action_scale=1, frame_skip=5, timestep_start=100000, timestep_end=100000):
        self.quick_init(locals())

        self.step_count = 0
        self.timestep_start = timestep_start
        self.timestep_end = timestep_end

        MultitaskEnv.__init__(self)
        self.action_scale = action_scale
        MujocoEnv.__init__(self, self.model_name, frame_skip=frame_skip)
        bounds = self.model.actuator_ctrlrange.copy()
        low = bounds[:, 0]
        high = bounds[:, 1]
        self.action_space = Box(low=low, high=high)
        obs_size = self._get_env_obs().shape[0]
        high = np.inf * np.ones(obs_size)
        low = -high
        self.obs_space = Box(low, high)
        self.observation_space = Dict([
            ('observation', self.obs_space),
            ('state_observation', self.obs_space),
        ])
        self.reset()


    @property
    def model_name(self):
        return get_asset_full_path('classic_mujoco/hopper.xml')

    def step(self, a):
        self.step_count += 1

        posbefore = self.sim.data.qpos[0]

        if self.step_count >= self.timestep_start and self.step_count <= self.timestep_end:
            a[0] = 0
            a[1] = 0


        self.do_simulation(a, self.frame_skip)
        posafter, height, ang = self.sim.data.qpos[0:3]
        alive_bonus = 1.0
        current_velocity = (posafter - posbefore) / self.dt
        
        if current_velocity > 5:
            reward = 5
        else:
            reward = current_velocity

        reward += alive_bonus
        reward -= 1e-3 * np.square(a).sum()
        s = self.state_vector()
        done = not (np.isfinite(s).all() and (np.abs(s[2:]) < 100).all() and
                    (height > .7) and (abs(ang) < .2))
        ob = self._get_obs()
        info = self._get_info()
        return ob, reward, done, info

    def _get_env_obs(self):
        return np.concatenate([
            self.sim.data.qpos.flat[1:],
            np.clip(self.sim.data.qvel.flat, -10, 10)
        ])

    def _get_obs(self):
        state_obs = self._get_env_obs()
        return dict(
            observation=state_obs,
            state_observation=state_obs,
        )

    def _get_info(self, ):
        info = dict()
        return info
    
    def compute_rewards(self, actions, obs):
        pass

    def reset_model(self):
        self.step_count = 0
        qpos = self.init_qpos + self.np_random.uniform(low=-.005, high=.005, size=self.model.nq)
        qvel = self.init_qvel + self.np_random.uniform(low=-.005, high=.005, size=self.model.nv)
        self.set_state(qpos, qvel)
        return self._get_obs()

    def viewer_setup(self):
        self.viewer.cam.trackbodyid = 2
        self.viewer.cam.distance = self.model.stat.extent * 0.75
        self.viewer.cam.lookat[2] = 1.15
        self.viewer.cam.elevation = -20

    def reset(self):
        self.step_count = 0
        self.reset_model()
        return self._get_obs()

    def get_diagnostics(self, paths, prefix=''):
        statistics = OrderedDict()
        return statistics

    def get_goal(self):
        return None
    
    def sample_goals(self):
        return None
