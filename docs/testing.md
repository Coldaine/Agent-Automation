## Verification and Coordinates

### Visual Verification

The agent uses a visual verification mechanism to confirm that an action has had an effect on the screen. It does this by taking a screenshot before and after the action and comparing them. The difference between the two images is calculated as a delta value. If the delta is above a certain threshold, the action is considered successful.

#### Verification Thresholds

The verification thresholds can be configured in the `config.yaml` file. The following thresholds are available:

- `click_delta_threshold`: The minimum delta for a click action to be considered successful.
- `double_click_delta_threshold`: The minimum delta for a double-click action to be considered successful.
- `right_click_delta_threshold`: The minimum delta for a right-click action to be considered successful.
- `type_delta_threshold`: The minimum delta for a type action to be considered successful.
- `scroll_delta_threshold`: The minimum delta for a scroll action to be considered successful.
- `drag_delta_threshold`: The minimum delta for a drag action to be considered successful.

#### Retry on No Visual Change

If the initial verification fails, the agent can be configured to retry the verification. This is useful in cases where the screen content changes slowly or not at all. The retry mechanism can be configured in the `config.yaml` file with the following options:

- `enabled`: Whether to enable the retry mechanism.
- `max_retries`: The maximum number of times to retry the verification.
- `jitter_px`: The number of pixels to jitter the mouse by before retrying the verification.
- `enlarge_factor`: The factor by which to enlarge the verification region before retrying the verification.

### Accepted Coordinate Shapes

The agent accepts a variety of coordinate shapes for pointer actions. The following shapes are supported:

- `x,y`: `{"x": 100, "y": 200}`
- `cx,cy`: `{"cx": 100, "cy": 200}`
- `coordinates`: `{"coordinates": [100, 200]}`
- `point`: `{"point": [100, 200]}`
- `position`: `{"position": {"x": 100, "y": 200}}`
- `center`: `{"center": {"x": 100, "y": 200}}`
- `target`: `{"target": [100, 200]}`
- `location`: `{"location": [100, 200]}`
- `bbox`: `{"bbox": [100, 200, 300, 400]}`

The agent also supports normalized coordinates. The following coordinate systems are supported:

- `normalized_1000`: Coordinates are in the range 0-1000.
- `unit_normalized`: Coordinates are in the range 0-1.