__doc__ = """ Mesh Initializer using Pyvista """

import pyvista as pv
import numpy as np


class Mesh():
    """
    This Mesh Initializer class uses pyvista to import mesh files in the
    STL or OBJ file formats and initializes the necessary mesh information.

    How to initialize a mesh?
    -------------------------

    mesh = Mesh(r"<filepath>")

    Notes:
    ------

    - Please be sure to add .stl / .obj at the end of the filepath, if already present, ignore.

    Attributes:
    -----------

    mesh.faces:
        - Stores the coordinates of the 3 vertices of each of the n faces of the imported mesh.
        - Dimension: (3 spatial coordinates, 3 vertices, n faces)

    mesh.face_normals:
        - Stores the coordinates of the unit normal vector of each of the n faces.
        - Dimension: (3 spatial coordinates, n faces)

    mesh.face_centers:
        - Stores the coordinates of the position vector of each of the n face centers.
        - Dimension: (3 spatial coordinates, n faces)

    mesh.mesh_scale:
        - Stores the 3 dimensions of the smallest box that could fit the mesh.
        - Dimension: (3 spatial lengths)

    mesh.mesh_center:
        - Stores the coordinates of the position vector of the center of the smallest box that could fit the mesh.
        - Dimension: (3 spatial coordinates)
    """
    def __init__(self, filepath: str) -> None:
        self.mesh = pv.read(filepath)
        self.mesh_center = self.mesh.center
        self.pyvista_face_normals = self.mesh.face_normals
        self.pyvista_faces = self.mesh.faces
        self.number_of_faces = self.mesh.n_faces
        self.pyvista_points = self.mesh.points
        self.bounds = self.mesh.bounds
        self.face_normals = self.face_normal_calculation(self.pyvista_face_normals)
        self.faces = self.face_calculation(self.pyvista_faces, self.pyvista_points, self.number_of_faces)
        self.face_centers = self.face_center_calculation(self.faces, self.number_of_faces)
        self.mesh_scale = self.mesh_scale_calculation(self.bounds)

    def face_calculation(self, pvfaces: np.ndarray, meshpoints: np.ndarray, n_faces: int) -> np.ndarray:
        """
        This function converts the faces from pyvista to pyelastica geometry

        What the function does?:
        ------------------------

        # The pyvista's 'faces' attribute returns the connectivity array of the faces of the mesh.
            ex: [3, 0, 1, 2, 4, 0, 1, 3, 4]
            The faces array is organized as:
                [n0, p0_0, p0_1, ..., p0_n, n1, p1_0, p1_1, ..., p1_n, ...]
                    ,where n0 is the number of points in face 0, and pX_Y is the Y'th point in face X.
            For more info, refer to the api reference here - https://docs.pyvista.org/version/stable/api/core/_autosummary/pyvista.PolyData.faces.html

        # The pyvista's 'points' attribute returns the individual vertices of the mesh with no connection information.
            ex: [-1.  1. -1.]
                [ 1. -1. -1.]
                [ 1.  1. -1.]

        # This function takes the 'mesh.points' and numbers them as 0, 1, 2 ..., n_faces - 1;
          then establishes connection between verticies of same cell/face through the 'mesh.faces' array
          and returns an array with dimension (3 spatial coordinates, 3 vertices, n faces), where n_faces is the number of faces in the mesh.

        Notes:
        ------

        - This function has been tested for triangular meshes only.
        """
        faces = np.zeros((3, 3, n_faces))
        vertice_no = 0

        for i in range(n_faces):
            vertice_no += 1
            for j in range(3):
                faces[..., j, i] = meshpoints[pvfaces[vertice_no]]
                vertice_no += 1

        return faces

    def face_normal_calculation(self, pyvista_face_normals: np.ndarray) -> np.ndarray:
        """
        This function converts the face normals from pyvista to pyelastica geometry,
        in pyelastica the face are stored in the format of (n_faces, 3 spatial coordinates),
        this is converted into (3 spatial coordinates, n_faces).
        """
        face_normals = np.transpose(pyvista_face_normals)

        return face_normals

    def face_center_calculation(self, faces: np.ndarray, n_faces: int) -> np.ndarray:
        """
        This function calculates the position vector of each face of the mesh
        simply by averaging all the vertices of every face/cell.
        """
        face_centers = np.zeros((3, n_faces))

        for i in range(n_faces):
            for j in range(3):
                temp_sum = faces[j][..., i].sum()
                face_centers[j][i] = temp_sum / 3

        return face_centers

    def mesh_scale_calculation(self, bounds: np.ndarray) -> np.ndarray:
        """
        This function calculates scale of the mesh,
        for that it calculates the maximum distance between mesh's farthest verticies in each axis.
        """
        scale = np.zeros(3)
        axis = 0
        for i in range(0, 5, 2):
            scale[axis] = bounds[i + 1] - bounds[i]
            axis += 1

        return scale