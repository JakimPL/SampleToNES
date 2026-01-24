from typing import NamedTuple

from sampletones.constants.enums import FeatureKey, GeneratorName
from sampletones.types.feature import FeatureValue


class ReconstructionUpdate(NamedTuple):
    generator_name: GeneratorName
    feature_key: FeatureKey
    data: FeatureValue
