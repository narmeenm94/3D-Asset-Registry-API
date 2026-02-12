"""
3D Model Metadata Extraction Service.
Automatically extracts geometry and material information from uploaded 3D assets.
Supports glTF/GLB, OBJ, STL, PLY, and other common formats via trimesh.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Extracts metadata from 3D model files.
    Uses trimesh for geometry analysis and pygltflib for glTF-specific data.
    """
    
    # Supported formats and their extensions
    SUPPORTED_FORMATS = {
        "glb": "model/gltf-binary",
        "gltf": "model/gltf+json", 
        "obj": "model/obj",
        "stl": "model/stl",
        "ply": "model/ply",
        "fbx": "application/octet-stream",
        "usdz": "model/vnd.usdz+zip",
        "blend": "application/x-blender",
    }
    
    # Formats that trimesh can parse directly
    TRIMESH_FORMATS = {"glb", "gltf", "obj", "stl", "ply", "off", "dae"}
    
    # Formats that need pygltflib
    GLTF_FORMATS = {"glb", "gltf"}
    
    def __init__(self):
        self._trimesh = None
        self._pygltflib = None
    
    @property
    def trimesh(self):
        """Lazy load trimesh."""
        if self._trimesh is None:
            try:
                import trimesh
                self._trimesh = trimesh
            except ImportError:
                logger.warning("trimesh not installed - geometry extraction disabled")
        return self._trimesh
    
    @property
    def pygltflib(self):
        """Lazy load pygltflib."""
        if self._pygltflib is None:
            try:
                import pygltflib
                self._pygltflib = pygltflib
            except ImportError:
                logger.warning("pygltflib not installed - glTF-specific extraction disabled")
        return self._pygltflib
    
    async def extract(
        self,
        file_content: bytes,
        filename: str,
        file_format: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract metadata from a 3D model file.
        
        Args:
            file_content: Raw bytes of the 3D file
            filename: Original filename
            file_format: Optional format hint (e.g., 'glb', 'obj')
            
        Returns:
            Dictionary with extracted metadata
        """
        # Determine format from filename if not provided
        if not file_format:
            file_format = Path(filename).suffix.lstrip(".").lower()
        
        metadata = {
            "extracted": True,
            "format_detected": file_format,
            "file_size_bytes": len(file_content),
        }
        
        # Extract geometry data with trimesh
        if file_format in self.TRIMESH_FORMATS and self.trimesh:
            geometry_data = await self._extract_with_trimesh(file_content, filename, file_format)
            metadata.update(geometry_data)
        
        # Extract glTF-specific data
        if file_format in self.GLTF_FORMATS and self.pygltflib:
            gltf_data = await self._extract_gltf_data(file_content, file_format)
            metadata.update(gltf_data)
        
        return metadata
    
    async def _extract_with_trimesh(
        self,
        file_content: bytes,
        filename: str,
        file_format: str,
    ) -> dict[str, Any]:
        """Extract geometry metadata using trimesh."""
        try:
            # Write to temp file for trimesh to read
            with tempfile.NamedTemporaryFile(
                suffix=f".{file_format}",
                delete=False
            ) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            
            try:
                # Load the mesh
                scene_or_mesh = self.trimesh.load(tmp_path)
                
                # Handle both Scene and Mesh objects
                if isinstance(scene_or_mesh, self.trimesh.Scene):
                    return self._extract_from_scene(scene_or_mesh)
                else:
                    return self._extract_from_mesh(scene_or_mesh)
                    
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.warning(f"Failed to extract geometry with trimesh: {e}")
            return {"extraction_error": str(e)}
    
    def _extract_from_mesh(self, mesh) -> dict[str, Any]:
        """Extract metadata from a single mesh."""
        data = {}
        
        try:
            # Basic geometry counts
            if hasattr(mesh, "vertices") and mesh.vertices is not None:
                data["vertex_count"] = len(mesh.vertices)
            
            if hasattr(mesh, "faces") and mesh.faces is not None:
                data["tri_count"] = len(mesh.faces)
            
            # Bounding box
            if hasattr(mesh, "bounds") and mesh.bounds is not None:
                bounds = mesh.bounds
                data["bounding_box"] = {
                    "min": {"x": float(bounds[0][0]), "y": float(bounds[0][1]), "z": float(bounds[0][2])},
                    "max": {"x": float(bounds[1][0]), "y": float(bounds[1][1]), "z": float(bounds[1][2])},
                }
                # Calculate dimensions
                extents = bounds[1] - bounds[0]
                data["dimensions"] = {
                    "width": float(extents[0]),
                    "height": float(extents[1]),
                    "depth": float(extents[2]),
                }
            
            # Check for vertex colors
            if hasattr(mesh, "visual"):
                visual = mesh.visual
                if hasattr(visual, "vertex_colors") and visual.vertex_colors is not None:
                    data["has_vertex_colors"] = True
                if hasattr(visual, "uv") and visual.uv is not None:
                    data["has_uv_coordinates"] = True
            
            # Mesh properties
            if hasattr(mesh, "is_watertight"):
                data["is_watertight"] = bool(mesh.is_watertight)
            
            if hasattr(mesh, "is_volume"):
                data["is_volume"] = bool(mesh.is_volume)
                
        except Exception as e:
            logger.warning(f"Error extracting mesh properties: {e}")
        
        return data
    
    def _extract_from_scene(self, scene) -> dict[str, Any]:
        """Extract metadata from a scene with multiple meshes."""
        data = {
            "is_scene": True,
            "mesh_count": len(scene.geometry) if scene.geometry else 0,
        }
        
        total_vertices = 0
        total_faces = 0
        
        try:
            # Aggregate data from all meshes
            for name, geometry in scene.geometry.items():
                if hasattr(geometry, "vertices") and geometry.vertices is not None:
                    total_vertices += len(geometry.vertices)
                if hasattr(geometry, "faces") and geometry.faces is not None:
                    total_faces += len(geometry.faces)
            
            data["vertex_count"] = total_vertices
            data["tri_count"] = total_faces
            
            # Scene bounding box
            if hasattr(scene, "bounds") and scene.bounds is not None:
                bounds = scene.bounds
                data["bounding_box"] = {
                    "min": {"x": float(bounds[0][0]), "y": float(bounds[0][1]), "z": float(bounds[0][2])},
                    "max": {"x": float(bounds[1][0]), "y": float(bounds[1][1]), "z": float(bounds[1][2])},
                }
                extents = bounds[1] - bounds[0]
                data["dimensions"] = {
                    "width": float(extents[0]),
                    "height": float(extents[1]),
                    "depth": float(extents[2]),
                }
                
        except Exception as e:
            logger.warning(f"Error extracting scene properties: {e}")
        
        return data
    
    async def _extract_gltf_data(
        self,
        file_content: bytes,
        file_format: str,
    ) -> dict[str, Any]:
        """Extract glTF-specific metadata using pygltflib."""
        try:
            if file_format == "glb":
                gltf = self.pygltflib.GLTF2.load_from_bytes(file_content)
            else:
                # For .gltf, we'd need the JSON content
                # This is simplified - full implementation would parse JSON
                return {}
            
            data = {}
            
            # -------------------------------------------------------
            # Read METRO metadata from glTF scene extras.
            # The Blender plugin embeds structured metadata here via
            # its glTF export hook (metro_metadata key in scene extras).
            # -------------------------------------------------------
            metro_from_extras = self._read_metro_extras(gltf)
            if metro_from_extras:
                data["metro_embedded"] = metro_from_extras
                logger.info(
                    "Found embedded METRO metadata in glTF extras: %d fields",
                    len(metro_from_extras),
                )
            
            # Materials
            if gltf.materials:
                data["material_count"] = len(gltf.materials)
                data["has_materials"] = True
                data["material_names"] = [
                    m.name for m in gltf.materials if m.name
                ][:10]  # Limit to first 10
            
            # Textures
            if gltf.textures:
                data["texture_count"] = len(gltf.textures)
                data["has_textures"] = True
            
            # Animations
            if gltf.animations:
                data["animation_count"] = len(gltf.animations)
                data["has_animations"] = True
                data["animation_names"] = [
                    a.name for a in gltf.animations if a.name
                ][:10]
            
            # Meshes
            if gltf.meshes:
                data["gltf_mesh_count"] = len(gltf.meshes)
            
            # Nodes (hierarchy)
            if gltf.nodes:
                data["node_count"] = len(gltf.nodes)
            
            # Skins (skeletal animation)
            if gltf.skins:
                data["has_skeleton"] = True
                data["skin_count"] = len(gltf.skins)
            
            # Cameras
            if gltf.cameras:
                data["camera_count"] = len(gltf.cameras)
            
            # Asset info
            if gltf.asset:
                if gltf.asset.generator:
                    data["generator"] = gltf.asset.generator
                if gltf.asset.version:
                    data["gltf_version"] = gltf.asset.version
                if gltf.asset.copyright:
                    data["copyright"] = gltf.asset.copyright
            
            return data
            
        except Exception as e:
            logger.warning(f"Failed to extract glTF data: {e}")
            return {"gltf_extraction_error": str(e)}

    def _read_metro_extras(self, gltf) -> dict[str, Any] | None:
        """
        Read METRO metadata embedded in glTF scene extras.

        The Blender plugin stores metadata under scene.extras["metro_metadata"].
        This method checks all scenes and returns the first match.

        Returns:
            dict with METRO metadata fields, or None if not found.
        """
        import json as _json

        if not gltf.scenes:
            return None

        for scene in gltf.scenes:
            extras = getattr(scene, "extras", None)
            if extras is None:
                continue

            metro = None

            if isinstance(extras, dict):
                metro = extras.get("metro_metadata")
            elif isinstance(extras, str):
                try:
                    parsed = _json.loads(extras)
                    if isinstance(parsed, dict):
                        metro = parsed.get("metro_metadata")
                except (ValueError, _json.JSONDecodeError):
                    pass

            if metro and isinstance(metro, dict):
                return metro

        return None
    
    def get_mime_type(self, file_format: str) -> str | None:
        """Get MIME type for a file format."""
        return self.SUPPORTED_FORMATS.get(file_format.lower())
    
    def is_supported(self, file_format: str) -> bool:
        """Check if a format is supported for extraction."""
        return file_format.lower() in self.SUPPORTED_FORMATS


# Singleton instance
_extractor: MetadataExtractor | None = None


def get_metadata_extractor() -> MetadataExtractor:
    """Get the singleton metadata extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = MetadataExtractor()
    return _extractor
