from game.ui.camera import camera_origin

VIEW = (40, 15)
MAP = (64, 48)


def test_player_is_centered_in_the_middle_of_the_map():
    assert camera_origin(32, 24, *MAP, *VIEW) == (12, 17)


def test_camera_stops_at_top_left():
    assert camera_origin(0, 0, *MAP, *VIEW) == (0, 0)


def test_camera_stops_at_bottom_right():
    assert camera_origin(63, 47, *MAP, *VIEW) == (24, 33)


def test_small_map_is_centered():
    assert camera_origin(2, 2, 20, 10, *VIEW) == (-10, -2)
