import functools

from matplotlib._api.deprecation import MatplotlibDeprecationWarning
from matplotlib.backend_bases import MouseEvent
import matplotlib.colors as mcolors
import matplotlib.widgets as widgets
import matplotlib.pyplot as plt
from matplotlib.testing.decorators import check_figures_equal, image_comparison
from matplotlib.testing.widgets import (click_and_drag, do_event, get_ax,
                                        mock_event, noop)

import numpy as np
from numpy.testing import assert_allclose

import pytest


@pytest.fixture
def ax():
    return get_ax()


def check_rectangle(**kwargs):
    ax = get_ax()

    def onselect(epress, erelease):
        ax._got_onselect = True
        assert epress.xdata == 100
        assert epress.ydata == 100
        assert erelease.xdata == 199
        assert erelease.ydata == 199

    tool = widgets.RectangleSelector(ax, onselect, **kwargs)
    do_event(tool, 'press', xdata=100, ydata=100, button=1)
    do_event(tool, 'onmove', xdata=199, ydata=199, button=1)

    # purposely drag outside of axis for release
    do_event(tool, 'release', xdata=250, ydata=250, button=1)

    if kwargs.get('drawtype', None) not in ['line', 'none']:
        assert_allclose(tool.geometry,
                        [[100., 100, 199, 199, 100],
                         [100, 199, 199, 100, 100]],
                        err_msg=tool.geometry)

    assert ax._got_onselect


def test_rectangle_selector():
    check_rectangle()

    with pytest.warns(
        MatplotlibDeprecationWarning,
            match="Support for drawtype='line' is deprecated"):
        check_rectangle(drawtype='line', useblit=False)

    check_rectangle(useblit=True, button=1)

    with pytest.warns(
        MatplotlibDeprecationWarning,
            match="Support for drawtype='none' is deprecated"):
        check_rectangle(drawtype='none', minspanx=10, minspany=10)

    check_rectangle(minspanx=10, minspany=10, spancoords='pixels')
    check_rectangle(props=dict(fill=True))


@pytest.mark.parametrize('spancoords', ['data', 'pixels'])
@pytest.mark.parametrize('minspanx, x1', [[0, 10], [1, 10.5], [1, 11]])
@pytest.mark.parametrize('minspany, y1', [[0, 10], [1, 10.5], [1, 11]])
def test_rectangle_minspan(ax, spancoords, minspanx, x1, minspany, y1):
    # attribute to track number of onselect calls
    ax._n_onselect = 0

    def onselect(epress, erelease):
        ax._n_onselect += 1
        ax._epress = epress
        ax._erelease = erelease

    x0, y0 = (10, 10)
    if spancoords == 'pixels':
        minspanx, minspany = (ax.transData.transform((x1, y1)) -
                              ax.transData.transform((x0, y0)))

    tool = widgets.RectangleSelector(ax, onselect, interactive=True,
                                     spancoords=spancoords,
                                     minspanx=minspanx, minspany=minspany)
    # Too small to create a selector
    click_and_drag(tool, start=(x0, x1), end=(y0, y1))
    assert not tool._selection_completed
    assert ax._n_onselect == 0

    click_and_drag(tool, start=(20, 20), end=(30, 30))
    assert tool._selection_completed
    assert ax._n_onselect == 1

    # Too small to create a selector. Should clear existing selector, and
    # trigger onselect because there was a preexisting selector
    click_and_drag(tool, start=(x0, y0), end=(x1, y1))
    assert not tool._selection_completed
    assert ax._n_onselect == 2
    assert ax._epress.xdata == x0
    assert ax._epress.ydata == y0
    assert ax._erelease.xdata == x1
    assert ax._erelease.ydata == y1


def test_deprecation_selector_visible_attribute():
    ax = get_ax()
    tool = widgets.RectangleSelector(ax, lambda *args: None)

    assert tool.get_visible()

    with pytest.warns(
        MatplotlibDeprecationWarning,
            match="was deprecated in Matplotlib 3.6"):
        tool.visible = False
    assert not tool.get_visible()


@pytest.mark.parametrize('drag_from_anywhere, new_center',
                         [[True, (60, 75)],
                          [False, (30, 20)]])
def test_rectangle_drag(ax, drag_from_anywhere, new_center):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True,
                                     drag_from_anywhere=drag_from_anywhere)
    # Create rectangle
    click_and_drag(tool, start=(0, 10), end=(100, 120))
    assert tool.center == (50, 65)
    # Drag inside rectangle, but away from centre handle
    #
    # If drag_from_anywhere == True, this will move the rectangle by (10, 10),
    # giving it a new center of (60, 75)
    #
    # If drag_from_anywhere == False, this will create a new rectangle with
    # center (30, 20)
    click_and_drag(tool, start=(25, 15), end=(35, 25))
    assert tool.center == new_center
    # Check that in both cases, dragging outside the rectangle draws a new
    # rectangle
    click_and_drag(tool, start=(175, 185), end=(185, 195))
    assert tool.center == (180, 190)


def test_rectangle_selector_set_props_handle_props(ax):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True,
                                     props=dict(facecolor='b', alpha=0.2),
                                     handle_props=dict(alpha=0.5))
    # Create rectangle
    click_and_drag(tool, start=(0, 10), end=(100, 120))

    artist = tool._selection_artist
    assert artist.get_facecolor() == mcolors.to_rgba('b', alpha=0.2)
    tool.set_props(facecolor='r', alpha=0.3)
    assert artist.get_facecolor() == mcolors.to_rgba('r', alpha=0.3)

    for artist in tool._handles_artists:
        assert artist.get_markeredgecolor() == 'black'
        assert artist.get_alpha() == 0.5
    tool.set_handle_props(markeredgecolor='r', alpha=0.3)
    for artist in tool._handles_artists:
        assert artist.get_markeredgecolor() == 'r'
        assert artist.get_alpha() == 0.3


def test_rectangle_resize(ax):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    # Create rectangle
    click_and_drag(tool, start=(0, 10), end=(100, 120))
    assert tool.extents == (0.0, 100.0, 10.0, 120.0)

    # resize NE handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[3]
    xdata_new, ydata_new = xdata + 10, ydata + 5
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert tool.extents == (extents[0], xdata_new, extents[2], ydata_new)

    # resize E handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdata_new, ydata_new = xdata + 10, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert tool.extents == (extents[0], xdata_new, extents[2], extents[3])

    # resize W handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdata_new, ydata_new = xdata + 15, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert tool.extents == (xdata_new, extents[1], extents[2], extents[3])

    # resize SW handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2]
    xdata_new, ydata_new = xdata + 20, ydata + 25
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert tool.extents == (xdata_new, extents[1], ydata_new, extents[3])


def test_rectangle_add_state(ax):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    # Create rectangle
    click_and_drag(tool, start=(70, 65), end=(125, 130))

    with pytest.raises(ValueError):
        tool.add_state('unsupported_state')

    with pytest.raises(ValueError):
        tool.add_state('clear')
    tool.add_state('move')
    tool.add_state('square')
    tool.add_state('center')


@pytest.mark.parametrize('add_state', [True, False])
def test_rectangle_resize_center(ax, add_state):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    # Create rectangle
    click_and_drag(tool, start=(70, 65), end=(125, 130))
    assert tool.extents == (70.0, 125.0, 65.0, 130.0)

    if add_state:
        tool.add_state('center')
        use_key = None
    else:
        use_key = 'control'

    # resize NE handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[3]
    xdiff, ydiff = 10, 5
    xdata_new, ydata_new = xdata + xdiff, ydata + ydiff
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0] - xdiff, xdata_new,
                            extents[2] - ydiff, ydata_new)

    # resize E handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = 10
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0] - xdiff, xdata_new,
                            extents[2], extents[3])

    # resize E handle negative diff
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = -20
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0] - xdiff, xdata_new,
                            extents[2], extents[3])

    # resize W handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = 15
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (xdata_new, extents[1] - xdiff,
                            extents[2], extents[3])

    # resize W handle negative diff
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = -25
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (xdata_new, extents[1] - xdiff,
                            extents[2], extents[3])

    # resize SW handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2]
    xdiff, ydiff = 20, 25
    xdata_new, ydata_new = xdata + xdiff, ydata + ydiff
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (xdata_new, extents[1] - xdiff,
                            ydata_new, extents[3] - ydiff)


@pytest.mark.parametrize('add_state', [True, False])
def test_rectangle_resize_square(ax, add_state):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    # Create rectangle
    click_and_drag(tool, start=(70, 65), end=(120, 115))
    assert tool.extents == (70.0, 120.0, 65.0, 115.0)

    if add_state:
        tool.add_state('square')
        use_key = None
    else:
        use_key = 'shift'

    # resize NE handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[3]
    xdiff, ydiff = 10, 5
    xdata_new, ydata_new = xdata + xdiff, ydata + ydiff
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0], xdata_new,
                            extents[2], extents[3] + xdiff)

    # resize E handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = 10
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0], xdata_new,
                            extents[2], extents[3] + xdiff)

    # resize E handle negative diff
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = -20
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0], xdata_new,
                            extents[2], extents[3] + xdiff)

    # resize W handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = 15
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (xdata_new, extents[1],
                            extents[2], extents[3] - xdiff)

    # resize W handle negative diff
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = -25
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (xdata_new, extents[1],
                            extents[2], extents[3] - xdiff)

    # resize SW handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2]
    xdiff, ydiff = 20, 25
    xdata_new, ydata_new = xdata + xdiff, ydata + ydiff
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new),
                   key=use_key)
    assert tool.extents == (extents[0] + ydiff, extents[1],
                            ydata_new, extents[3])


def test_rectangle_resize_square_center(ax):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    # Create rectangle
    click_and_drag(tool, start=(70, 65), end=(120, 115))
    tool.add_state('square')
    tool.add_state('center')
    assert_allclose(tool.extents, (70.0, 120.0, 65.0, 115.0))

    # resize NE handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[3]
    xdiff, ydiff = 10, 5
    xdata_new, ydata_new = xdata + xdiff, ydata + ydiff
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert_allclose(tool.extents, (extents[0] - xdiff, xdata_new,
                                   extents[2] - xdiff, extents[3] + xdiff))

    # resize E handle
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = 10
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert_allclose(tool.extents, (extents[0] - xdiff, xdata_new,
                                   extents[2] - xdiff, extents[3] + xdiff))

    # resize E handle negative diff
    extents = tool.extents
    xdata, ydata = extents[1], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = -20
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert_allclose(tool.extents, (extents[0] - xdiff, xdata_new,
                                   extents[2] - xdiff, extents[3] + xdiff))

    # resize W handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = 5
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert_allclose(tool.extents, (xdata_new, extents[1] - xdiff,
                                   extents[2] + xdiff, extents[3] - xdiff))

    # resize W handle negative diff
    extents = tool.extents
    xdata, ydata = extents[0], extents[2] + (extents[3] - extents[2]) / 2
    xdiff = -25
    xdata_new, ydata_new = xdata + xdiff, ydata
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert_allclose(tool.extents, (xdata_new, extents[1] - xdiff,
                                   extents[2] + xdiff, extents[3] - xdiff))

    # resize SW handle
    extents = tool.extents
    xdata, ydata = extents[0], extents[2]
    xdiff, ydiff = 20, 25
    xdata_new, ydata_new = xdata + xdiff, ydata + ydiff
    click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
    assert_allclose(tool.extents, (extents[0] + ydiff, extents[1] - ydiff,
                                   ydata_new, extents[3] - ydiff))


@pytest.mark.parametrize('selector_class',
                         [widgets.RectangleSelector, widgets.EllipseSelector])
def test_rectangle_rotate(ax, selector_class):
    tool = selector_class(ax, onselect=noop, interactive=True)
    # Draw rectangle
    click_and_drag(tool, start=(100, 100), end=(130, 140))
    assert tool.extents == (100, 130, 100, 140)
    assert len(tool._state) == 0

    # Rotate anticlockwise using top-right corner
    do_event(tool, 'on_key_press', key='r')
    assert tool._state == set(['rotate'])
    assert len(tool._state) == 1
    click_and_drag(tool, start=(130, 140), end=(120, 145))
    do_event(tool, 'on_key_press', key='r')
    assert len(tool._state) == 0
    # Extents shouldn't change (as shape of rectangle hasn't changed)
    assert tool.extents == (100, 130, 100, 140)
    assert_allclose(tool.rotation, 25.56, atol=0.01)
    tool.rotation = 45
    assert tool.rotation == 45
    # Corners should move
    assert_allclose(tool.corners,
                    np.array([[118.53, 139.75, 111.46, 90.25],
                              [95.25, 116.46, 144.75, 123.54]]), atol=0.01)

    # Scale using top-right corner
    click_and_drag(tool, start=(110, 145), end=(110, 160))
    assert_allclose(tool.extents, (100, 139.75, 100, 151.82), atol=0.01)

    if selector_class == widgets.RectangleSelector:
        with pytest.raises(ValueError):
            tool._selection_artist.rotation_point = 'unvalid_value'


def test_rectangle_add_remove_set(ax):
    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    # Draw rectangle
    click_and_drag(tool, start=(100, 100), end=(130, 140))
    assert tool.extents == (100, 130, 100, 140)
    assert len(tool._state) == 0
    for state in ['rotate', 'square', 'center']:
        tool.add_state(state)
        assert len(tool._state) == 1
        tool.remove_state(state)
        assert len(tool._state) == 0


@pytest.mark.parametrize('use_data_coordinates', [False, True])
def test_rectangle_resize_square_center_aspect(ax, use_data_coordinates):
    ax.set_aspect(0.8)

    tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True,
                                     use_data_coordinates=use_data_coordinates)
    # Create rectangle
    click_and_drag(tool, start=(70, 65), end=(120, 115))
    assert tool.extents == (70.0, 120.0, 65.0, 115.0)
    tool.add_state('square')
    tool.add_state('center')

    if use_data_coordinates:
        # resize E handle
        extents = tool.extents
        xdata, ydata, width = extents[1], extents[3], extents[1] - extents[0]
        xdiff, ycenter = 10,  extents[2] + (extents[3] - extents[2]) / 2
        xdata_new, ydata_new = xdata + xdiff, ydata
        ychange = width / 2 + xdiff
        click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
        assert_allclose(tool.extents, [extents[0] - xdiff, xdata_new,
                                       ycenter - ychange, ycenter + ychange])
    else:
        # resize E handle
        extents = tool.extents
        xdata, ydata = extents[1], extents[3]
        xdiff = 10
        xdata_new, ydata_new = xdata + xdiff, ydata
        ychange = xdiff * 1 / tool._aspect_ratio_correction
        click_and_drag(tool, start=(xdata, ydata), end=(xdata_new, ydata_new))
        assert_allclose(tool.extents, [extents[0] - xdiff, xdata_new,
                                       46.25, 133.75])


def test_ellipse(ax):
    """For ellipse, test out the key modifiers"""
    tool = widgets.EllipseSelector(ax, onselect=noop,
                                   grab_range=10, interactive=True)
    tool.extents = (100, 150, 100, 150)

    # drag the rectangle
    click_and_drag(tool, start=(125, 125), end=(145, 145))
    assert tool.extents == (120, 170, 120, 170)

    # create from center
    click_and_drag(tool, start=(100, 100), end=(125, 125), key='control')
    assert tool.extents == (75, 125, 75, 125)

    # create a square
    click_and_drag(tool, start=(10, 10), end=(35, 30), key='shift')
    extents = [int(e) for e in tool.extents]
    assert extents == [10, 35, 10, 35]

    # create a square from center
    click_and_drag(tool, start=(100, 100), end=(125, 130), key='ctrl+shift')
    extents = [int(e) for e in tool.extents]
    assert extents == [70, 130, 70, 130]

    assert tool.geometry.shape == (2, 73)
    assert_allclose(tool.geometry[:, 0], [70., 100])


def test_rectangle_handles(ax):
    tool = widgets.RectangleSelector(ax, onselect=noop,
                                     grab_range=10,
                                     interactive=True,
                                     handle_props={'markerfacecolor': 'r',
                                                   'markeredgecolor': 'b'})
    tool.extents = (100, 150, 100, 150)

    assert_allclose(tool.corners, ((100, 150, 150, 100), (100, 100, 150, 150)))
    assert tool.extents == (100, 150, 100, 150)
    assert_allclose(tool.edge_centers,
                    ((100, 125.0, 150, 125.0), (125.0, 100, 125.0, 150)))
    assert tool.extents == (100, 150, 100, 150)

    # grab a corner and move it
    click_and_drag(tool, start=(100, 100), end=(120, 120))
    assert tool.extents == (120, 150, 120, 150)

    # grab the center and move it
    click_and_drag(tool, start=(132, 132), end=(120, 120))
    assert tool.extents == (108, 138, 108, 138)

    # create a new rectangle
    click_and_drag(tool, start=(10, 10), end=(100, 100))
    assert tool.extents == (10, 100, 10, 100)

    # Check that marker_props worked.
    assert mcolors.same_color(
        tool._corner_handles.artists[0].get_markerfacecolor(), 'r')
    assert mcolors.same_color(
        tool._corner_handles.artists[0].get_markeredgecolor(), 'b')


@pytest.mark.parametrize('interactive', [True, False])
def test_rectangle_selector_onselect(ax, interactive):
    # check when press and release events take place at the same position
    def onselect(vmin, vmax):
        ax._got_onselect = True

    tool = widgets.RectangleSelector(ax, onselect, interactive=interactive)
    # move outside of axis
    click_and_drag(tool, start=(100, 110), end=(150, 120))

    assert tool.ax._got_onselect
    assert tool.extents == (100.0, 150.0, 110.0, 120.0)

    # Reset tool.ax._got_onselect
    tool.ax._got_onselect = False
    click_and_drag(tool, start=(10, 100), end=(10, 100))

    assert tool.ax._got_onselect


@pytest.mark.parametrize('ignore_event_outside', [True, False])
def test_rectangle_selector_ignore_outside(ax, ignore_event_outside):
    def onselect(vmin, vmax):
        ax._got_onselect = True

    tool = widgets.RectangleSelector(ax, onselect,
                                     ignore_event_outside=ignore_event_outside)
    click_and_drag(tool, start=(100, 110), end=(150, 120))
    assert tool.ax._got_onselect
    assert tool.extents == (100.0, 150.0, 110.0, 120.0)

    # Reset
    ax._got_onselect = False
    # Trigger event outside of span
    click_and_drag(tool, start=(150, 150), end=(160, 160))
    if ignore_event_outside:
        # event have been ignored and span haven't changed.
        assert not ax._got_onselect
        assert tool.extents == (100.0, 150.0, 110.0, 120.0)
    else:
        # A new shape is created
        assert ax._got_onselect
        assert tool.extents == (150.0, 160.0, 150.0, 160.0)


def check_span(*args, **kwargs):
    ax = get_ax()

    def onselect(vmin, vmax):
        ax._got_onselect = True
        assert vmin == 100
        assert vmax == 199

    def onmove(vmin, vmax):
        assert vmin == 100
        assert vmax == 199
        ax._got_on_move = True

    if 'onmove_callback' in kwargs:
        kwargs['onmove_callback'] = onmove

    tool = widgets.SpanSelector(ax, onselect, *args, **kwargs)
    do_event(tool, 'press', xdata=100, ydata=100, button=1)
    # move outside of axis
    do_event(tool, 'onmove', xdata=199, ydata=199, button=1)
    do_event(tool, 'release', xdata=250, ydata=250, button=1)

    assert ax._got_onselect

    if 'onmove_callback' in kwargs:
        assert ax._got_on_move


def test_span_selector():
    check_span('horizontal', minspan=10, useblit=True)
    check_span('vertical', onmove_callback=True, button=1)
    check_span('horizontal', props=dict(fill=True))
    check_span('horizontal', interactive=True)


@pytest.mark.parametrize('interactive', [True, False])
def test_span_selector_onselect(ax, interactive):
    def onselect(vmin, vmax):
        ax._got_onselect = True

    tool = widgets.SpanSelector(ax, onselect, 'horizontal',
                                interactive=interactive)
    # move outside of axis
    click_and_drag(tool, start=(100, 100), end=(150, 100))
    assert tool.ax._got_onselect
    assert tool.extents == (100, 150)

    # Reset tool.ax._got_onselect
    tool.ax._got_onselect = False
    click_and_drag(tool, start=(10, 100), end=(10, 100))
    assert tool.ax._got_onselect


@pytest.mark.parametrize('ignore_event_outside', [True, False])
def test_span_selector_ignore_outside(ax, ignore_event_outside):
    def onselect(vmin, vmax):
        ax._got_onselect = True

    def onmove(vmin, vmax):
        ax._got_on_move = True

    tool = widgets.SpanSelector(ax, onselect, 'horizontal',
                                onmove_callback=onmove,
                                ignore_event_outside=ignore_event_outside)
    click_and_drag(tool, start=(100, 100), end=(125, 125))
    assert ax._got_onselect
    assert ax._got_on_move
    assert tool.extents == (100, 125)

    # Reset
    ax._got_onselect = False
    ax._got_on_move = False
    # Trigger event outside of span
    click_and_drag(tool, start=(150, 150), end=(160, 160))
    if ignore_event_outside:
        # event have been ignored and span haven't changed.
        assert not ax._got_onselect
        assert not ax._got_on_move
        assert tool.extents == (100, 125)
    else:
        # A new shape is created
        assert ax._got_onselect
        assert ax._got_on_move
        assert tool.extents == (150, 160)


@pytest.mark.parametrize('drag_from_anywhere', [True, False])
def test_span_selector_drag(ax, drag_from_anywhere):
    # Create span
    tool = widgets.SpanSelector(ax, onselect=noop, direction='horizontal',
                                interactive=True,
                                drag_from_anywhere=drag_from_anywhere)
    click_and_drag(tool, start=(10, 10), end=(100, 120))
    assert tool.extents == (10, 100)
    # Drag inside span
    #
    # If drag_from_anywhere == True, this will move the span by 10,
    # giving new value extents = 20, 110
    #
    # If drag_from_anywhere == False, this will create a new span with
    # value extents = 25, 35
    click_and_drag(tool, start=(25, 15), end=(35, 25))
    if drag_from_anywhere:
        assert tool.extents == (20, 110)
    else:
        assert tool.extents == (25, 35)

    # Check that in both cases, dragging outside the span draws a new span
    click_and_drag(tool, start=(175, 185), end=(185, 195))
    assert tool.extents == (175, 185)


def test_span_selector_direction(ax):
    tool = widgets.SpanSelector(ax, onselect=noop, direction='horizontal',
                                interactive=True)
    assert tool.direction == 'horizontal'
    assert tool._edge_handles.direction == 'horizontal'

    with pytest.raises(ValueError):
        tool = widgets.SpanSelector(ax, onselect=noop,
                                    direction='invalid_direction')

    tool.direction = 'vertical'
    assert tool.direction == 'vertical'
    assert tool._edge_handles.direction == 'vertical'

    with pytest.raises(ValueError):
        tool.direction = 'invalid_string'


def test_span_selector_set_props_handle_props(ax):
    tool = widgets.SpanSelector(ax, onselect=noop, direction='horizontal',
                                interactive=True,
                                props=dict(facecolor='b', alpha=0.2),
                                handle_props=dict(alpha=0.5))
    # Create rectangle
    click_and_drag(tool, start=(0, 10), end=(100, 120))

    artist = tool._selection_artist
    assert artist.get_facecolor() == mcolors.to_rgba('b', alpha=0.2)
    tool.set_props(facecolor='r', alpha=0.3)
    assert artist.get_facecolor() == mcolors.to_rgba('r', alpha=0.3)

    for artist in tool._handles_artists:
        assert artist.get_color() == 'b'
        assert artist.get_alpha() == 0.5
    tool.set_handle_props(color='r', alpha=0.3)
    for artist in tool._handles_artists:
        assert artist.get_color() == 'r'
        assert artist.get_alpha() == 0.3


@pytest.mark.parametrize('selector', ['span', 'rectangle'])
def test_selector_clear(ax, selector):
    kwargs = dict(ax=ax, onselect=noop, interactive=True)
    if selector == 'span':
        Selector = widgets.SpanSelector
        kwargs['direction'] = 'horizontal'
    else:
        Selector = widgets.RectangleSelector

    tool = Selector(**kwargs)
    click_and_drag(tool, start=(10, 10), end=(100, 120))

    # press-release event outside the selector to clear the selector
    click_and_drag(tool, start=(130, 130), end=(130, 130))
    assert not tool._selection_completed

    kwargs['ignore_event_outside'] = True
    tool = Selector(**kwargs)
    assert tool.ignore_event_outside
    click_and_drag(tool, start=(10, 10), end=(100, 120))

    # press-release event outside the selector ignored
    click_and_drag(tool, start=(130, 130), end=(130, 130))
    assert tool._selection_completed

    do_event(tool, 'on_key_press', key='escape')
    assert not tool._selection_completed


@pytest.mark.parametrize('selector', ['span', 'rectangle'])
def test_selector_clear_method(ax, selector):
    if selector == 'span':
        tool = widgets.SpanSelector(ax, onselect=noop, direction='horizontal',
                                    interactive=True,
                                    ignore_event_outside=True)
    else:
        tool = widgets.RectangleSelector(ax, onselect=noop, interactive=True)
    click_and_drag(tool, start=(10, 10), end=(100, 120))
    assert tool._selection_completed
    assert tool.get_visible()
    if selector == 'span':
        assert tool.extents == (10, 100)

    tool.clear()
    assert not tool._selection_completed
    assert not tool.get_visible()

    # Do another cycle of events to make sure we can
    click_and_drag(tool, start=(10, 10), end=(50, 120))
    assert tool._selection_completed
    assert tool.get_visible()
    if selector == 'span':
        assert tool.extents == (10, 50)


def test_span_selector_add_state(ax):
    tool = widgets.SpanSelector(ax, noop, 'horizontal',
                                interactive=True)

    with pytest.raises(ValueError):
        tool.add_state('unsupported_state')
    with pytest.raises(ValueError):
        tool.add_state('center')
    with pytest.raises(ValueError):
        tool.add_state('square')

    tool.add_state('move')


def test_tool_line_handle(ax):
    positions = [20, 30, 50]
    tool_line_handle = widgets.ToolLineHandles(ax, positions, 'horizontal',
                                               useblit=False)

    for artist in tool_line_handle.artists:
        assert not artist.get_animated()
        assert not artist.get_visible()

    tool_line_handle.set_visible(True)
    tool_line_handle.set_animated(True)

    for artist in tool_line_handle.artists:
        assert artist.get_animated()
        assert artist.get_visible()

    assert tool_line_handle.positions == positions


@pytest.mark.parametrize('direction', ("horizontal", "vertical"))
def test_span_selector_bound(direction):
    fig, ax = plt.subplots(1, 1)
    ax.plot([10, 20], [10, 30])
    ax.figure.canvas.draw()
    x_bound = ax.get_xbound()
    y_bound = ax.get_ybound()

    tool = widgets.SpanSelector(ax, print, direction, interactive=True)
    assert ax.get_xbound() == x_bound
    assert ax.get_ybound() == y_bound

    bound = x_bound if direction == 'horizontal' else y_bound
    assert tool._edge_handles.positions == list(bound)

    press_data = [10.5, 11.5]
    move_data = [11, 13]  # Updating selector is done in onmove
    release_data = move_data
    click_and_drag(tool, start=press_data, end=move_data)

    assert ax.get_xbound() == x_bound
    assert ax.get_ybound() == y_bound

    index = 0 if direction == 'horizontal' else 1
    handle_positions = [press_data[index], release_data[index]]
    assert tool._edge_handles.positions == handle_positions


@pytest.mark.backend('QtAgg', skip_on_importerror=True)
def test_span_selector_animated_artists_callback():
    """Check that the animated artists changed in callbacks are updated."""
    x = np.linspace(0, 2 * np.pi, 100)
    values = np.sin(x)

    fig, ax = plt.subplots()
    (ln,) = ax.plot(x, values, animated=True)
    (ln2, ) = ax.plot([], animated=True)

    # spin the event loop to let the backend process any pending operations
    # before drawing artists
    # See blitting tutorial
    plt.pause(0.1)
    ax.draw_artist(ln)
    fig.canvas.blit(fig.bbox)

    def mean(vmin, vmax):
        # Return mean of values in x between *vmin* and *vmax*
        indmin, indmax = np.searchsorted(x, (vmin, vmax))
        v = values[indmin:indmax].mean()
        ln2.set_data(x, v)

    span = widgets.SpanSelector(ax, mean, direction='horizontal',
                                onmove_callback=mean,
                                interactive=True,
                                drag_from_anywhere=True,
                                useblit=True)

    # Add span selector and check that the line is draw after it was updated
    # by the callback
    press_data = [1, 2]
    move_data = [2, 2]
    do_event(span, 'press', xdata=press_data[0], ydata=press_data[1], button=1)
    do_event(span, 'onmove', xdata=move_data[0], ydata=move_data[1], button=1)
    assert span._get_animated_artists() == (ln, ln2)
    assert ln.stale is False
    assert ln2.stale
    assert ln2.get_ydata() == 0.9547335049088455
    span.update()
    assert ln2.stale is False

    # Change span selector and check that the line is drawn/updated after its
    # value was updated by the callback
    press_data = [4, 2]
    move_data = [5, 2]
    release_data = [5, 2]
    do_event(span, 'press', xdata=press_data[0], ydata=press_data[1], button=1)
    do_event(span, 'onmove', xdata=move_data[0], ydata=move_data[1], button=1)
    assert ln.stale is False
    assert ln2.stale
    assert ln2.get_ydata() == -0.9424150707548072
    do_event(span, 'release', xdata=release_data[0],
             ydata=release_data[1], button=1)
    assert ln2.stale is False


def test_snapping_values_span_selector(ax):
    def onselect(*args):
        pass

    tool = widgets.SpanSelector(ax, onselect, direction='horizontal',)
    snap_function = tool._snap

    snap_values = np.linspace(0, 5, 11)
    values = np.array([-0.1, 0.1, 0.2, 0.5, 0.6, 0.7, 0.9, 4.76, 5.0, 5.5])
    expect = np.array([00.0, 0.0, 0.0, 0.5, 0.5, 0.5, 1.0, 5.00, 5.0, 5.0])
    values = snap_function(values, snap_values)
    assert_allclose(values, expect)


def test_span_selector_snap(ax):
    def onselect(vmin, vmax):
        ax._got_onselect = True

    snap_values = np.arange(50) * 4

    tool = widgets.SpanSelector(ax, onselect, direction='horizontal',
                                snap_values=snap_values)
    tool.extents = (17, 35)
    assert tool.extents == (16, 36)

    tool.snap_values = None
    assert tool.snap_values is None
    tool.extents = (17, 35)
    assert tool.extents == (17, 35)


def check_lasso_selector(**kwargs):
    ax = get_ax()

    def onselect(verts):
        ax._got_onselect = True
        assert verts == [(100, 100), (125, 125), (150, 150)]

    tool = widgets.LassoSelector(ax, onselect, **kwargs)
    do_event(tool, 'press', xdata=100, ydata=100, button=1)
    do_event(tool, 'onmove', xdata=125, ydata=125, button=1)
    do_event(tool, 'release', xdata=150, ydata=150, button=1)

    assert ax._got_onselect


def test_lasso_selector():
    check_lasso_selector()
    check_lasso_selector(useblit=False, props=dict(color='red'))
    check_lasso_selector(useblit=True, button=1)


def test_CheckButtons(ax):
    check = widgets.CheckButtons(ax, ('a', 'b', 'c'), (True, False, True))
    assert check.get_status() == [True, False, True]
    check.set_active(0)
    assert check.get_status() == [False, False, True]

    cid = check.on_clicked(lambda: None)
    check.disconnect(cid)


@pytest.mark.parametrize("toolbar", ["none", "toolbar2", "toolmanager"])
def test_TextBox(ax, toolbar):
    # Avoid "toolmanager is provisional" warning.
    dict.__setitem__(plt.rcParams, "toolbar", toolbar)

    from unittest.mock import Mock
    submit_event = Mock()
    text_change_event = Mock()
    tool = widgets.TextBox(ax, '')
    tool.on_submit(submit_event)
    tool.on_text_change(text_change_event)

    assert tool.text == ''

    do_event(tool, '_click')

    tool.set_val('x**2')

    assert tool.text == 'x**2'
    assert text_change_event.call_count == 1

    tool.begin_typing(tool.text)
    tool.stop_typing()

    assert submit_event.call_count == 2

    do_event(tool, '_click')
    do_event(tool, '_keypress', key='+')
    do_event(tool, '_keypress', key='5')

    assert text_change_event.call_count == 3


@image_comparison(['check_radio_buttons.png'], style='mpl20', remove_text=True)
def test_check_radio_buttons_image():
    ax = get_ax()
    # Remove this line when this test image is regenerated.
    plt.rcParams['text.kerning_factor'] = 6

    plt.subplots_adjust(left=0.3)
    rax1 = plt.axes([0.05, 0.7, 0.15, 0.15])
    rax2 = plt.axes([0.05, 0.2, 0.15, 0.15])
    widgets.RadioButtons(rax1, ('Radio 1', 'Radio 2', 'Radio 3'))
    widgets.CheckButtons(rax2, ('Check 1', 'Check 2', 'Check 3'),
                         (False, True, True))


@image_comparison(['check_bunch_of_radio_buttons.png'],
                  style='mpl20', remove_text=True)
def test_check_bunch_of_radio_buttons():
    rax = plt.axes([0.05, 0.1, 0.15, 0.7])
    widgets.RadioButtons(rax, ('B1', 'B2', 'B3', 'B4', 'B5', 'B6',
                               'B7', 'B8', 'B9', 'B10', 'B11', 'B12',
                               'B13', 'B14', 'B15'))


def test_slider_slidermin_slidermax_invalid():
    fig, ax = plt.subplots()
    # test min/max with floats
    with pytest.raises(ValueError):
        widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                       slidermin=10.0)
    with pytest.raises(ValueError):
        widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                       slidermax=10.0)


def test_slider_slidermin_slidermax():
    fig, ax = plt.subplots()
    slider_ = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                             valinit=5.0)

    slider = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                            valinit=1.0, slidermin=slider_)
    assert slider.val == slider_.val

    slider = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                            valinit=10.0, slidermax=slider_)
    assert slider.val == slider_.val


def test_slider_valmin_valmax():
    fig, ax = plt.subplots()
    slider = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                            valinit=-10.0)
    assert slider.val == slider.valmin

    slider = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                            valinit=25.0)
    assert slider.val == slider.valmax


def test_slider_valstep_snapping():
    fig, ax = plt.subplots()
    slider = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                            valinit=11.4, valstep=1)
    assert slider.val == 11

    slider = widgets.Slider(ax=ax, label='', valmin=0.0, valmax=24.0,
                            valinit=11.4, valstep=[0, 1, 5.5, 19.7])
    assert slider.val == 5.5


def test_slider_horizontal_vertical():
    fig, ax = plt.subplots()
    slider = widgets.Slider(ax=ax, label='', valmin=0, valmax=24,
                            valinit=12, orientation='horizontal')
    slider.set_val(10)
    assert slider.val == 10
    # check the dimension of the slider patch in axes units
    box = slider.poly.get_extents().transformed(ax.transAxes.inverted())
    assert_allclose(box.bounds, [0, .25, 10/24, .5])

    fig, ax = plt.subplots()
    slider = widgets.Slider(ax=ax, label='', valmin=0, valmax=24,
                            valinit=12, orientation='vertical')
    slider.set_val(10)
    assert slider.val == 10
    # check the dimension of the slider patch in axes units
    box = slider.poly.get_extents().transformed(ax.transAxes.inverted())
    assert_allclose(box.bounds, [.25, 0, .5, 10/24])


def test_slider_reset():
    fig, ax = plt.subplots()
    slider = widgets.Slider(ax=ax, label='', valmin=0, valmax=1, valinit=.5)
    slider.set_val(0.75)
    slider.reset()
    assert slider.val == 0.5


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_range_slider(orientation):
    if orientation == "vertical":
        idx = [1, 0, 3, 2]
    else:
        idx = [0, 1, 2, 3]

    fig, ax = plt.subplots()

    slider = widgets.RangeSlider(
        ax=ax, label="", valmin=0.0, valmax=1.0, orientation=orientation,
        valinit=[0.1, 0.34]
    )
    box = slider.poly.get_extents().transformed(ax.transAxes.inverted())
    assert_allclose(box.get_points().flatten()[idx], [0.1, 0.25, 0.34, 0.75])

    # Check initial value is set correctly
    assert_allclose(slider.val, (0.1, 0.34))

    def handle_positions(slider):
        if orientation == "vertical":
            return [h.get_ydata()[0] for h in slider._handles]
        else:
            return [h.get_xdata()[0] for h in slider._handles]

    slider.set_val((0.2, 0.6))
    assert_allclose(slider.val, (0.2, 0.6))
    assert_allclose(handle_positions(slider), (0.2, 0.6))

    box = slider.poly.get_extents().transformed(ax.transAxes.inverted())
    assert_allclose(box.get_points().flatten()[idx], [0.2, .25, 0.6, .75])

    slider.set_val((0.2, 0.1))
    assert_allclose(slider.val, (0.1, 0.2))
    assert_allclose(handle_positions(slider), (0.1, 0.2))

    slider.set_val((-1, 10))
    assert_allclose(slider.val, (0, 1))
    assert_allclose(handle_positions(slider), (0, 1))

    slider.reset()
    assert_allclose(slider.val, (0.1, 0.34))
    assert_allclose(handle_positions(slider), (0.1, 0.34))


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_range_slider_same_init_values(orientation):
    if orientation == "vertical":
        idx = [1, 0, 3, 2]
    else:
        idx = [0, 1, 2, 3]

    fig, ax = plt.subplots()

    slider = widgets.RangeSlider(
         ax=ax, label="", valmin=0.0, valmax=1.0, orientation=orientation,
         valinit=[0, 0]
     )
    box = slider.poly.get_extents().transformed(ax.transAxes.inverted())
    assert_allclose(box.get_points().flatten()[idx], [0, 0.25, 0, 0.75])


def check_polygon_selector(event_sequence, expected_result, selections_count,
                           **kwargs):
    """
    Helper function to test Polygon Selector.

    Parameters
    ----------
    event_sequence : list of tuples (etype, dict())
        A sequence of events to perform. The sequence is a list of tuples
        where the first element of the tuple is an etype (e.g., 'onmove',
        'press', etc.), and the second element of the tuple is a dictionary of
         the arguments for the event (e.g., xdata=5, key='shift', etc.).
    expected_result : list of vertices (xdata, ydata)
        The list of vertices that are expected to result from the event
        sequence.
    selections_count : int
        Wait for the tool to call its `onselect` function `selections_count`
        times, before comparing the result to the `expected_result`
    **kwargs
        Keyword arguments are passed to PolygonSelector.
    """
    ax = get_ax()

    ax._selections_count = 0

    def onselect(vertices):
        ax._selections_count += 1
        ax._current_result = vertices

    tool = widgets.PolygonSelector(ax, onselect, **kwargs)

    for (etype, event_args) in event_sequence:
        do_event(tool, etype, **event_args)

    assert ax._selections_count == selections_count
    assert ax._current_result == expected_result


def polygon_place_vertex(xdata, ydata):
    return [('onmove', dict(xdata=xdata, ydata=ydata)),
            ('press', dict(xdata=xdata, ydata=ydata)),
            ('release', dict(xdata=xdata, ydata=ydata))]


def polygon_remove_vertex(xdata, ydata):
    return [('onmove', dict(xdata=xdata, ydata=ydata)),
            ('press', dict(xdata=xdata, ydata=ydata, button=3)),
            ('release', dict(xdata=xdata, ydata=ydata, button=3))]


@pytest.mark.parametrize('draw_bounding_box', [False, True])
def test_polygon_selector(draw_bounding_box):
    check_selector = functools.partial(
        check_polygon_selector, draw_bounding_box=draw_bounding_box)

    # Simple polygon
    expected_result = [(50, 50), (150, 50), (50, 150)]
    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 50))
    check_selector(event_sequence, expected_result, 1)

    # Move first vertex before completing the polygon.
    expected_result = [(75, 50), (150, 50), (50, 150)]
    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + [('on_key_press', dict(key='control')),
                         ('onmove', dict(xdata=50, ydata=50)),
                         ('press', dict(xdata=50, ydata=50)),
                         ('onmove', dict(xdata=75, ydata=50)),
                         ('release', dict(xdata=75, ydata=50)),
                         ('on_key_release', dict(key='control'))]
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(75, 50))
    check_selector(event_sequence, expected_result, 1)

    # Move first two vertices at once before completing the polygon.
    expected_result = [(50, 75), (150, 75), (50, 150)]
    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + [('on_key_press', dict(key='shift')),
                         ('onmove', dict(xdata=100, ydata=100)),
                         ('press', dict(xdata=100, ydata=100)),
                         ('onmove', dict(xdata=100, ydata=125)),
                         ('release', dict(xdata=100, ydata=125)),
                         ('on_key_release', dict(key='shift'))]
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 75))
    check_selector(event_sequence, expected_result, 1)

    # Move first vertex after completing the polygon.
    expected_result = [(75, 50), (150, 50), (50, 150)]
    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 50)
                      + [('onmove', dict(xdata=50, ydata=50)),
                         ('press', dict(xdata=50, ydata=50)),
                         ('onmove', dict(xdata=75, ydata=50)),
                         ('release', dict(xdata=75, ydata=50))])
    check_selector(event_sequence, expected_result, 2)

    # Move all vertices after completing the polygon.
    expected_result = [(75, 75), (175, 75), (75, 175)]
    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 50)
                      + [('on_key_press', dict(key='shift')),
                         ('onmove', dict(xdata=100, ydata=100)),
                         ('press', dict(xdata=100, ydata=100)),
                         ('onmove', dict(xdata=125, ydata=125)),
                         ('release', dict(xdata=125, ydata=125)),
                         ('on_key_release', dict(key='shift'))])
    check_selector(event_sequence, expected_result, 2)

    # Try to move a vertex and move all before placing any vertices.
    expected_result = [(50, 50), (150, 50), (50, 150)]
    event_sequence = ([('on_key_press', dict(key='control')),
                       ('onmove', dict(xdata=100, ydata=100)),
                       ('press', dict(xdata=100, ydata=100)),
                       ('onmove', dict(xdata=125, ydata=125)),
                       ('release', dict(xdata=125, ydata=125)),
                       ('on_key_release', dict(key='control')),
                       ('on_key_press', dict(key='shift')),
                       ('onmove', dict(xdata=100, ydata=100)),
                       ('press', dict(xdata=100, ydata=100)),
                       ('onmove', dict(xdata=125, ydata=125)),
                       ('release', dict(xdata=125, ydata=125)),
                       ('on_key_release', dict(key='shift'))]
                      + polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 50))
    check_selector(event_sequence, expected_result, 1)

    # Try to place vertex out-of-bounds, then reset, and start a new polygon.
    expected_result = [(50, 50), (150, 50), (50, 150)]
    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(250, 50)
                      + [('on_key_press', dict(key='escape')),
                         ('on_key_release', dict(key='escape'))]
                      + polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 50))
    check_selector(event_sequence, expected_result, 1)


@pytest.mark.parametrize('draw_bounding_box', [False, True])
def test_polygon_selector_set_props_handle_props(ax, draw_bounding_box):
    ax._selections_count = 0

    def onselect(vertices):
        ax._selections_count += 1
        ax._current_result = vertices

    tool = widgets.PolygonSelector(ax, onselect,
                                   props=dict(color='b', alpha=0.2),
                                   handle_props=dict(alpha=0.5),
                                   draw_bounding_box=draw_bounding_box)

    event_sequence = (polygon_place_vertex(50, 50)
                      + polygon_place_vertex(150, 50)
                      + polygon_place_vertex(50, 150)
                      + polygon_place_vertex(50, 50))

    for (etype, event_args) in event_sequence:
        do_event(tool, etype, **event_args)

    artist = tool._selection_artist
    assert artist.get_color() == 'b'
    assert artist.get_alpha() == 0.2
    tool.set_props(color='r', alpha=0.3)
    assert artist.get_color() == 'r'
    assert artist.get_alpha() == 0.3

    for artist in tool._handles_artists:
        assert artist.get_color() == 'b'
        assert artist.get_alpha() == 0.5
    tool.set_handle_props(color='r', alpha=0.3)
    for artist in tool._handles_artists:
        assert artist.get_color() == 'r'
        assert artist.get_alpha() == 0.3


@check_figures_equal()
def test_rect_visibility(fig_test, fig_ref):
    # Check that requesting an invisible selector makes it invisible
    ax_test = fig_test.subplots()
    _ = fig_ref.subplots()

    tool = widgets.RectangleSelector(ax_test, onselect=noop,
                                     props={'visible': False})
    tool.extents = (0.2, 0.8, 0.3, 0.7)


# Change the order that the extra point is inserted in
@pytest.mark.parametrize('idx', [1, 2, 3])
@pytest.mark.parametrize('draw_bounding_box', [False, True])
def test_polygon_selector_remove(idx, draw_bounding_box):
    verts = [(50, 50), (150, 50), (50, 150)]
    event_sequence = [polygon_place_vertex(*verts[0]),
                      polygon_place_vertex(*verts[1]),
                      polygon_place_vertex(*verts[2]),
                      # Finish the polygon
                      polygon_place_vertex(*verts[0])]
    # Add an extra point
    event_sequence.insert(idx, polygon_place_vertex(200, 200))
    # Remove the extra point
    event_sequence.append(polygon_remove_vertex(200, 200))
    # Flatten list of lists
    event_sequence = sum(event_sequence, [])
    check_polygon_selector(event_sequence, verts, 2,
                           draw_bounding_box=draw_bounding_box)


@pytest.mark.parametrize('draw_bounding_box', [False, True])
def test_polygon_selector_remove_first_point(draw_bounding_box):
    verts = [(50, 50), (150, 50), (50, 150)]
    event_sequence = (polygon_place_vertex(*verts[0]) +
                      polygon_place_vertex(*verts[1]) +
                      polygon_place_vertex(*verts[2]) +
                      polygon_place_vertex(*verts[0]) +
                      polygon_remove_vertex(*verts[0]))
    check_polygon_selector(event_sequence, verts[1:], 2,
                           draw_bounding_box=draw_bounding_box)


@pytest.mark.parametrize('draw_bounding_box', [False, True])
def test_polygon_selector_redraw(ax, draw_bounding_box):
    verts = [(50, 50), (150, 50), (50, 150)]
    event_sequence = (polygon_place_vertex(*verts[0]) +
                      polygon_place_vertex(*verts[1]) +
                      polygon_place_vertex(*verts[2]) +
                      polygon_place_vertex(*verts[0]) +
                      # Polygon completed, now remove first two verts
                      polygon_remove_vertex(*verts[1]) +
                      polygon_remove_vertex(*verts[2]) +
                      # At this point the tool should be reset so we can add
                      # more vertices
                      polygon_place_vertex(*verts[1]))

    tool = widgets.PolygonSelector(ax, onselect=noop,
                                   draw_bounding_box=draw_bounding_box)
    for (etype, event_args) in event_sequence:
        do_event(tool, etype, **event_args)
    # After removing two verts, only one remains, and the
    # selector should be automatically resete
    assert tool.verts == verts[0:2]


@pytest.mark.parametrize('draw_bounding_box', [False, True])
@check_figures_equal(extensions=['png'])
def test_polygon_selector_verts_setter(fig_test, fig_ref, draw_bounding_box):
    verts = [(0.1, 0.4), (0.5, 0.9), (0.3, 0.2)]
    ax_test = fig_test.add_subplot()

    tool_test = widgets.PolygonSelector(
        ax_test, onselect=noop, draw_bounding_box=draw_bounding_box)
    tool_test.verts = verts
    assert tool_test.verts == verts

    ax_ref = fig_ref.add_subplot()
    tool_ref = widgets.PolygonSelector(
        ax_ref, onselect=noop, draw_bounding_box=draw_bounding_box)
    event_sequence = (polygon_place_vertex(*verts[0]) +
                      polygon_place_vertex(*verts[1]) +
                      polygon_place_vertex(*verts[2]) +
                      polygon_place_vertex(*verts[0]))
    for (etype, event_args) in event_sequence:
        do_event(tool_ref, etype, **event_args)


def test_polygon_selector_box(ax):
    # Create a diamond shape
    verts = [(20, 0), (0, 20), (20, 40), (40, 20)]
    event_sequence = (polygon_place_vertex(*verts[0]) +
                      polygon_place_vertex(*verts[1]) +
                      polygon_place_vertex(*verts[2]) +
                      polygon_place_vertex(*verts[3]) +
                      polygon_place_vertex(*verts[0]))

    # Create selector
    tool = widgets.PolygonSelector(ax, onselect=noop, draw_bounding_box=True)
    for (etype, event_args) in event_sequence:
        do_event(tool, etype, **event_args)

    # In order to trigger the correct callbacks, trigger events on the canvas
    # instead of the individual tools
    t = ax.transData
    canvas = ax.figure.canvas

    # Scale to half size using the top right corner of the bounding box
    MouseEvent(
        "button_press_event", canvas, *t.transform((40, 40)), 1)._process()
    MouseEvent(
        "motion_notify_event", canvas, *t.transform((20, 20)))._process()
    MouseEvent(
        "button_release_event", canvas, *t.transform((20, 20)), 1)._process()
    np.testing.assert_allclose(
        tool.verts, [(10, 0), (0, 10), (10, 20), (20, 10)])

    # Move using the center of the bounding box
    MouseEvent(
        "button_press_event", canvas, *t.transform((10, 10)), 1)._process()
    MouseEvent(
        "motion_notify_event", canvas, *t.transform((30, 30)))._process()
    MouseEvent(
        "button_release_event", canvas, *t.transform((30, 30)), 1)._process()
    np.testing.assert_allclose(
        tool.verts, [(30, 20), (20, 30), (30, 40), (40, 30)])

    # Remove a point from the polygon and check that the box extents update
    np.testing.assert_allclose(
        tool._box.extents, (20.0, 40.0, 20.0, 40.0))

    MouseEvent(
        "button_press_event", canvas, *t.transform((30, 20)), 3)._process()
    MouseEvent(
        "button_release_event", canvas, *t.transform((30, 20)), 3)._process()
    np.testing.assert_allclose(
        tool.verts, [(20, 30), (30, 40), (40, 30)])
    np.testing.assert_allclose(
        tool._box.extents, (20.0, 40.0, 30.0, 40.0))


@pytest.mark.parametrize(
    "horizOn, vertOn",
    [(True, True), (True, False), (False, True)],
)
def test_MultiCursor(horizOn, vertOn):
    (ax1, ax3) = plt.figure().subplots(2, sharex=True)
    ax2 = plt.figure().subplots()

    # useblit=false to avoid having to draw the figure to cache the renderer
    multi = widgets.MultiCursor(
        None, (ax1, ax2), useblit=False, horizOn=horizOn, vertOn=vertOn
    )

    # Only two of the axes should have a line drawn on them.
    if vertOn:
        assert len(multi.vlines) == 2
    if horizOn:
        assert len(multi.hlines) == 2

    # mock a motion_notify_event
    # Can't use `do_event` as that helper requires the widget
    # to have a single .ax attribute.
    event = mock_event(ax1, xdata=.5, ydata=.25)
    multi.onmove(event)

    # the lines in the first two ax should both move
    for l in multi.vlines:
        assert l.get_xdata() == (.5, .5)
    for l in multi.hlines:
        assert l.get_ydata() == (.25, .25)

    # test a move event in an Axes not part of the MultiCursor
    # the lines in ax1 and ax2 should not have moved.
    event = mock_event(ax3, xdata=.75, ydata=.75)
    multi.onmove(event)
    for l in multi.vlines:
        assert l.get_xdata() == (.5, .5)
    for l in multi.hlines:
        assert l.get_ydata() == (.25, .25)
