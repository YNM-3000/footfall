from footfall.geometry import BoundingBox, Line


def test_centroid_is_box_center():
    box = BoundingBox(10.0, 20.0, 30.0, 60.0)

    assert box.centroid == (20.0, 40.0)


def test_points_on_opposite_sides_get_opposite_signs():
    line = Line((0.0, 50.0), (100.0, 50.0))

    assert line.side_of((50.0, 10.0)) * line.side_of((50.0, 90.0)) < 0


def test_horizontal_midline_spans_frame_width_at_half_height():
    line = Line.horizontal_midline(width=640, height=480)

    assert line.p1 == (0.0, 240.0)
    assert line.p2 == (640.0, 240.0)


def test_int_endpoints_round_float_coordinates():
    line = Line((10.4, 20.6), (30.7, 40.2))

    assert line.int_endpoints == ((10, 21), (31, 40))


def test_from_coordinates_reads_x1_y1_x2_y2_order():
    line = Line.from_coordinates((1.0, 2.0, 3.0, 4.0))

    assert (line.p1, line.p2) == ((1.0, 2.0), (3.0, 4.0))
