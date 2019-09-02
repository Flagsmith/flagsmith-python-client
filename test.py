import logging
from bullet_train import BulletTrain;

logger = logging.getLogger(__name__)

bt = BulletTrain(environment_id="mJKERnxyQpeFK9GX6B8X2V")

logger.warning(bt.feature_enabled("sound_effects"))
logger.warning(bt.get_trait("blah", "ben"))
logger.warning(bt.set_trait("blah", "blahvalue2", "ben"))
logger.warning(bt.get_trait("blah", "ben"))
