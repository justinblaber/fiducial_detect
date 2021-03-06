# AUTOGENERATED! DO NOT EDIT! File to edit: gen_cb.ipynb (unless otherwise specified).

__all__ = ['meshgrid2ps', 'affine_ps', 'homography_ps', 'rotate_ps', 'get_circle_poly', 'rotate_poly', 'affine_poly',
           'poly2coords', 'affine_coords', 'homography_coords', 'plot_coords', 'euler2R', 'ARt2H', 'get_bb',
           'get_fiducial_poly', 'get_checker_poly', 'get_ps_b', 'get_ps_fp', 'get_ps_t', 'get_poly_cb', 'plot_cb_poly',
           'draw_ps', 'draw_coords']

# Cell
import copy

import descartes
import matplotlib.pyplot as plt
import numpy as np
import skimage.draw
import skimage.filters
import skimage.transform
from IPython.core.debugger import set_trace
from shapely import affinity
from shapely.geometry import Point, Polygon

# Cell
def meshgrid2ps(r_x, r_y, order='C'):
    xs, ys = np.meshgrid(r_x, r_y)
    return np.c_[xs.ravel(order), ys.ravel(order)]

# Cell
def _xform_ps(ps, mat):
    ps, mat = map(np.array, [ps,mat])
    ps_aug = np.concatenate([ps, np.ones((ps.shape[0], 1))], axis=1)
    return (mat@ps_aug.T).T

# Cell
def affine_ps(ps, mat):
    # Assumes last row of mat is [0, 0, 1]
    return _xform_ps(ps, mat)[:, 0:2]

# Cell
def homography_ps(ps, mat):
    ps = _xform_ps(ps, mat)
    return ps[:, 0:2]/ps[:, 2:]

# Cell
def rotate_ps(ps, deg):
    theta = np.radians(deg)
    R = [[np.cos(theta), -np.sin(theta), 0],
         [np.sin(theta),  np.cos(theta), 0],
         [            0,              0, 1]]
    return affine_ps(ps, R)

# Cell
def get_circle_poly(p, r):
     return Point(p).buffer(r)

# Cell
def rotate_poly(poly, deg):
    return affinity.rotate(poly, deg, origin=(0,0))

# Cell
def affine_poly(poly, mat):
    mat = np.array(mat)
    return affinity.affine_transform(poly, np.r_[mat[0:2,0:2].ravel(), mat[0,2], mat[1,2]])

# Cell
def poly2coords(poly):
    if isinstance(poly, Polygon):
        poly = [poly]

    coords = []
    for idx, p in enumerate(poly):
        coord = {}
        coord['ext'] = np.array(p.exterior.coords)
        coord['int'] = []
        for i in p.interiors:
            coord['int'].append(np.array(i.coords))
        coords.append(coord)

    return coords

# Cell
def _xform_coords(coords, mat, f_ps):
    coords = copy.deepcopy(coords)
    for coord in coords:
        coord['ext'] = f_ps(coord['ext'], mat)
        for idx in range(len(coord['int'])):
            coord['int'][idx] = f_ps(coord['int'][idx], mat)
    return coords

# Cell
def affine_coords(coords, mat):
    return _xform_coords(coords, mat, affine_ps)

# Cell
def homography_coords(coords, mat):
    return _xform_coords(coords, mat, homography_ps)

# Cell
def plot_coords(coords):
    plt.figure(figsize=(10,10))
    for coord in coords:
        plt.scatter(coord['ext'][:,0], coord['ext'][:,1], c='g')
        for ps_int in coord['int']:
            plt.scatter(ps_int[:,0], ps_int[:,1], c='r')

    plt.axis('equal')

# Cell
def euler2R(euler):
    theta_x, theta_y, theta_z = euler

    R_x = [[1,               0,                0],
           [0, np.cos(theta_x), -np.sin(theta_x)],
           [0, np.sin(theta_x),  np.cos(theta_x)]]

    R_y = [[ np.cos(theta_y), 0, np.sin(theta_y)],
           [               0, 1,               0],
           [-np.sin(theta_y), 0, np.cos(theta_y)]]

    R_z = [[np.cos(theta_z), -np.sin(theta_z), 0],
           [np.sin(theta_z),  np.cos(theta_z), 0],
           [              0,                0, 1]];

    R_x, R_y, R_z = map(np.array, [R_x, R_y, R_z])
    return R_z@R_y@R_x

# Cell
def ARt2H(A, R, t):
    A, R, t = map(np.array,[A, R, t])
    return A@np.c_[R[:,0:2], t]

# Cell
def get_bb(ps):
    return np.array([[ps[:,0].min(), ps[:,1].min()],
                     [ps[:,0].max(), ps[:,1].max()]])

# Cell
def get_fiducial_poly(num):
    # Returns fiducial marker normalized and centered around (0, 0)
    deg_pad = 46.1564

    # Get "outer" and "center" base polygons
    poly_o = get_circle_poly((0,0), 0.5).difference(get_circle_poly((0,0), 1/3))
    poly_c = get_circle_poly((0,0), 1/6)

    def _triangle(deg=0):
        p1 = np.array([[0, 0]])
        p2 = rotate_ps([[0, 1]], -deg_pad/2)
        p3 = rotate_ps([[0, 1]],  deg_pad/2)
        return rotate_poly(Polygon(np.concatenate([p1, p2, p3])), deg)

    def _circles(deg=0):
        poly_c1 = get_circle_poly(rotate_ps([[0, 5/12]], -deg_pad/2).ravel(), 1/12)
        poly_c2 = get_circle_poly(rotate_ps([[0, 5/12]],  deg_pad/2).ravel(), 1/12)
        return rotate_poly(poly_c1, deg), rotate_poly(poly_c2, deg)

    def _split(poly_o, deg):
        poly_t = _triangle(deg)
        poly_c1, poly_c2 = _circles(deg)
        return (poly_o.difference(poly_t)
                      .union(poly_c1)
                      .union(poly_c2))

    # Modify based on marker num
    if num == 1:
        pass # First marker has no splits
    elif 2 <= num <= 4:
        for deg in np.linspace(0, 360, num+1)[:-1]:
            poly_o = _split(poly_o, deg)
    else:
        raise RuntimeError(f'Invalid fiducial marker number: {num}')

    # Return polygon
    return poly_o.union(poly_c) # NOTE: I *think* this ordering may matter for drawing

# Cell
def get_checker_poly(i, j):
    # Returns checker target normalized and centered around (0, 0)
    poly_s1 = Polygon([[-.5, 0.5], [0.0, 0.5], [0.0, 0.0], [-.5, 0.0]])
    poly_s2 = Polygon([[0.0, 0.0], [0.5, 0.0], [0.5, -.5], [0.0, -.5]])
    poly = poly_s1.union(poly_s2)
    if np.mod(i+j, 2) == 1:
        poly = rotate_poly(poly, 90)
    return poly

# Cell
def get_ps_b(opts):
    h_cb, w_cb = opts['height_cb'], opts['width_cb']
    return meshgrid2ps([-w_cb/2, w_cb/2], [-h_cb/2, h_cb/2], 'F')

# Cell
def get_ps_fp(opts):
    h_fp, w_fp = opts['height_fp'], opts['width_fp'];
    return meshgrid2ps([-w_fp/2, w_fp/2], [-h_fp/2, h_fp/2], 'F')

# Cell
def get_ps_t(opts):
    s_t, num_t_w, num_t_h = opts['spacing_target'], opts['num_targets_width'], opts['num_targets_height']
    w_t, h_t = s_t*(num_t_w-1), s_t*(num_t_h-1)
    return meshgrid2ps(np.linspace(-w_t/2, w_t/2, num_t_w), np.linspace(h_t/2, -h_t/2, num_t_h))

# Cell
def get_poly_cb(f_fiducial_poly, f_target_poly, opts):
    # Get board
    ps_b = get_ps_b(opts)
    poly_cb = Polygon(ps_b[[0,2,3,1], :])

    # Subtract fiducial markers
    s_f = opts['size_fiducial']
    ps_fp = get_ps_fp(opts)
    for idx, p_fp in enumerate(ps_fp):
        fiducial_poly = f_fiducial_poly(idx+1)
        poly_cb = poly_cb.difference(affine_poly(fiducial_poly, [[s_f,   0, p_fp[0]],
                                                                 [  0, s_f, p_fp[1]],
                                                                 [  0,   0,      1]]))

    # Subtract targets
    sz_t, num_t_w, num_t_h = opts['size_target'], opts['num_targets_width'], opts['num_targets_height']
    ps_t = get_ps_t(opts)
    for idx, p_t in enumerate(ps_t):
        target_poly = f_target_poly(*np.unravel_index(idx, (num_t_h, num_t_w)))
        poly_cb = poly_cb.difference(affine_poly(target_poly, [[sz_t,    0, p_t[0]],
                                                               [   0, sz_t, p_t[1]],
                                                               [   0,    0,     1]]))

    return poly_cb

# Cell
def plot_cb_poly(cb_poly, opts):
    w_cb, h_cb = opts['width_cb'], opts['height_cb']
    plt.figure(figsize=(10,10))
    plt.gca().add_patch(descartes.PolygonPatch(cb_poly))
    plt.gca().set_xlim((-w_cb/2, w_cb/2))
    plt.gca().set_ylim((-h_cb/2, h_cb/2))
    plt.gca().set_aspect(1)

# Cell
def draw_ps(ps, img, val):
    i, j = [], []
    if ps.shape[0] > 0:
        j, i = skimage.draw.polygon(ps[:, 0], ps[:, 1], img.T.shape)
    img[i, j] = val
    return img

# Cell
def draw_coords(coords_cb, img, val_ext=1, val_int=0):
    for coord in coords_cb:
        draw_ps(coord['ext'], img, val_ext)
        for ps_int in coord['int']:
            draw_ps(ps_int, img, val_int)

    return img