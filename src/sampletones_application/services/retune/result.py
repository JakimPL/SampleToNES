from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.services.retune.sample import RetunedSample

RetuneResult = ServiceSuccess[RetunedSample] | ServiceError | ServiceCanceled
