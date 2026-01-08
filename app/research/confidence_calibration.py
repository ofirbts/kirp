import numpy as np

class ConfidenceCalibrator:
    def calibrate(self, confidences, correctness):
        # Simple logistic calibration
        x = np.array(confidences)
        y = np.array(correctness)
        slope = (y.mean() / x.mean()) if x.mean() > 0 else 1
        return slope
