import bpy
import re
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from bpy.types import Menu, Panel, UIList, UILayout
from . import Utils
from PIL import Image
FORMAT_EXT = {
    "bmp": "bmp",
    "dds": "dds",
    "hdr": "hdr",
    "targa": "tga",
    "jpeg": "jpg",
    "targa_raw": "tga",
    "targa": "tga",
    "png": "png"
}


def autoBlendMode(material):
    # Define the supported node types and inputs
    supported_node_types = ['BSDF_PRINCIPLED']
    supported_inputs = ['Base Color']

    # Get the shader node
    shader_node = next(
        (node for node in material.node_tree.nodes if node.type in supported_node_types), None)

    if shader_node is not None:
        for input_name in supported_inputs:
            # Get the input
            input = shader_node.inputs.get(input_name)

            if input is not None and input.is_linked:
                # Get the linked TEX_IMAGE node
                input_node = next(
                    (link.from_node for link in input.links if link.from_node.type == 'TEX_IMAGE'), None)

                if input_node is not None:
                    # Load the image using PIL
                    image = Image.open(bpy.path.abspath(
                        input_node.image.filepath))

                    # Check if the image has an alpha channel
                    if image.mode in ('RGBA', 'LA') and any(pixel[3] < 255 for pixel in image.getdata()):
                        # If the image has an alpha channel and at least one pixel is transparent,
                        # set the Blend Mode to Alpha Blend, Shadow Mode to Alpha Clip and Clip Threshold to 0.01
                        material.blend_method = 'BLEND'
                        material.shadow_method = 'CLIP'
                        material.alpha_threshold = 0.01
                    else:
                        # If the image does not have an alpha channel,
                        # set the Blend Mode and Shadow Mode to Opaque
                        material.blend_method = 'OPAQUE'
                        material.shadow_method = 'OPAQUE'


def loadPBRImages(materialName, path):
    pbrImages={
        "BaseColor":{
            "aliases":["BaseColor","Albedo"],
            "colorspace": "sRGB",
        },
        "Metallic":{
            "aliases": ["Metallic", "Metalness"],
            "colorspace": "Linear",
        },
        "Roughness":{
            "aliases":["Roughness","Rough"],
            "colorspace": "Linear",
        },
        "Normal":{
            "aliases":["Normal","NormalMap"],
            "colorspace": "normal",
        },
        "Emissive":{
            "aliases":["Emissive","EmissiveMap"],
            "colorspace": "sRGB",
        },
        "Occlusion":{
            "aliases":["Occlusion","AO"],
            "colorspace": "Linear",
        },        
    }
    out={}
    for k in pbrImages:
        outName = k.replace(' ', '').lower()
        for alias in pbrImages[k]["aliases"]:
            suffix = (materialName+"_"+alias).lower().strip()
            for file in os.listdir(path):
                fileWithoutExt = os.path.splitext(file)[0].lower().strip()
                ext = os.path.splitext(file)[1].lower().strip()[1:]
                if ext in FORMAT_EXT.values():
                    if fileWithoutExt.endswith(suffix):
                        out[outName] = {
                            "filepath":os.path.join(path,file)
                        }
                        break
                else: 
                    print("invalid format ext",ext)
            if outName in out:
                out[outName]["colorspace"] = pbrImages[k]["colorspace"]
                break
        
    return out


def loadPBRMaterial(obj, texturesPath):
    for matSlot in obj.material_slots:
        mat = matSlot.material
        if not mat:
            mat = bpy.data.materials.new(name=obj.name)
            matSlot.material = mat
        mat.use_nodes = True

        pbrImages = loadPBRImages(mat.name, texturesPath)
        
        # Get the material's node tree
        node_tree=mat.node_tree

        # Try to find an existing Principled BSDF node
        principled_bsdf_node = None
        for node in node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf_node = node
                break

        # If no Principled BSDF node was found, create a new one
        if principled_bsdf_node is None:
            principled_bsdf_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')

        # Find the Material Output node
        material_output_node = None
        for node in node_tree.nodes:
            if node.type == 'OUTPUT_MATERIAL':
                material_output_node = node
                break

        # If no Material Output node was found, create a new one
        if material_output_node is None:
            material_output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')

        # Link the Principled BSDF node to the Material Output node
        node_tree.links.new(principled_bsdf_node.outputs['BSDF'], material_output_node.inputs['Surface'])

        # Try to find an existing "glTF Material Output" group node
        gltf_material_output_node = None
        for node in node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree.name == 'glTF Material Output':
                gltf_material_output_node = node
                break

        # If no "glTF Material Output" group node was found, create a new one
        if gltf_material_output_node is None:
            # Create a new node group
            gltf_material_output_group = bpy.data.node_groups.new(
                'glTF Material Output', 'ShaderNodeTree')

            # Create group inputs
            group_inputs = gltf_material_output_group.nodes.new('NodeGroupInput')
            gltf_material_output_group.inputs.new('NodeSocketFloat', 'Occlusion')

            # Create group outputs
            group_outputs = gltf_material_output_group.nodes.new('NodeGroupOutput')
            gltf_material_output_group.outputs.new('NodeSocketFloat', 'Occlusion')

            # Link group input to group output
            gltf_material_output_group.links.new(
                group_inputs.outputs['Occlusion'], group_outputs.inputs['Occlusion'])

            # Create a new group node in the material's node tree and assign the new node group to it
            gltf_material_output_node = node_tree.nodes.new('ShaderNodeGroup')
            gltf_material_output_node.node_tree = gltf_material_output_group

            # Set default value for Occlusion input to 1
            gltf_material_output_node.inputs['Occlusion'].default_value = 1


        # Show AO in blender
        # Create a Shader Mix node
        shader_mix_node = node_tree.nodes.new('ShaderNodeMixShader')
        shader_mix_node.inputs['Fac'].default_value = 1

        # Create a black Emission shader
        black_shader_node_name = 'Prebaked Occlusion Render'
        black_shader_node = None
        # Check if a node with the same name already exists
        for node in node_tree.nodes:
            if node.name == black_shader_node_name:
                black_shader_node = node
                break
        if black_shader_node is None:
            black_shader_node = node_tree.nodes.new('ShaderNodeEmission')
            black_shader_node.inputs['Color'].default_value = (0, 0, 0, 1)

        # Connect the Principled BSDF output to the second shader input of the Shader Mix node
        node_tree.links.new(
            principled_bsdf_node.outputs['BSDF'], shader_mix_node.inputs[2])

        # Connect the black shader output to the first shader input of the Shader Mix node
        node_tree.links.new(
            black_shader_node.outputs['Emission'], shader_mix_node.inputs[1])

        # Connect the Shader Mix node output to the Material Output node
        node_tree.links.new(
            shader_mix_node.outputs['Shader'], material_output_node.inputs['Surface'])

        # Connect gltf_material_output_node Occlusion output to the Shader Mix node Fac input
        node_tree.links.new(
            gltf_material_output_node.outputs['Occlusion'], shader_mix_node.inputs['Fac'])



        # Load textures

        def handle_node_inputs(node, pbrImages, node_tree):
            for input in node.inputs:
                # Ignore space and case in the input name
                input_name = input.name.replace(' ', '').lower()

                # Check if the input name exists in pbrImages
                if input_name in pbrImages:
                    # Get the filepath and colorspace
                    img = pbrImages[input_name]
                    filepath = img['filepath']
                    colorspace = img['colorspace']

                    # Try to find an existing Image Texture node connected to this input
                    image_texture_node = None
                    for link in input.links:
                        if link.from_node.type == 'TEX_IMAGE':
                            image_texture_node = link.from_node
                            break

                    # If no Image Texture node was found, create a new one
                    if image_texture_node is None:
                        image_texture_node = node_tree.nodes.new('ShaderNodeTexImage')

                    # Update the image
                    print(filepath)
                    image_texture_node.image = bpy.data.images.load(filepath)

                    if colorspace.lower() == 'normal':
                        image_texture_node.image.colorspace_settings.name = 'Non-Color'

                        # Try to find an existing Normal Map node connected to this input
                        normal_map_node = None
                        for link in input.links:
                            if link.from_node.type == 'NORMAL_MAP':
                                normal_map_node = link.from_node
                                break

                        # If no Normal Map node was found, create a new one
                        if normal_map_node is None:
                            normal_map_node = node_tree.nodes.new(
                                'ShaderNodeNormalMap')

                        # Connect the Image Texture node to the Normal Map node
                        node_tree.links.new(
                            image_texture_node.outputs['Color'], normal_map_node.inputs['Color'])

                        # Connect the Normal Map node to the input
                        node_tree.links.new(normal_map_node.outputs['Normal'], input)
                    else:
                        # Set the color space
                        if colorspace.lower() == 'srgb':
                            image_texture_node.image.colorspace_settings.name = 'sRGB'
                        elif colorspace.lower() == 'linear':
                            image_texture_node.image.colorspace_settings.name = 'Non-Color'

                        # Connect the Image Texture node to the input
                        node_tree.links.new(image_texture_node.outputs['Color'], input)


        # Call the function for principled_bsdf_node and gltf_material_output_node
        handle_node_inputs(principled_bsdf_node, pbrImages, node_tree)
        handle_node_inputs(gltf_material_output_node, pbrImages, node_tree)

        Utils.rearrangeNodes(node_tree)
        autoBlendMode(mat)

        


class JME_TOOLS_automaterial_PBR(Operator, ExportHelper):
    bl_idname = "jmetools.automaterialpbr"
    bl_label = "Load PBR material from textures path"
    filename_ext = ""

    use_filter_folder = True
   
    def invoke(self, context, event):
        self.filepath = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        path = self.filepath
        if (not os.path.isdir(path)):
            path = os.path.split(os.path.abspath(path))[0]+os.path.sep
        print("Use "+path+" as texture path")
        for obj in bpy.context.scene.objects:
            if obj.select_get():
                loadPBRMaterial(obj, path)
        return {"FINISHED"}


class JME_TOOLS_PT_automaterial_panel(Panel):
    bl_label = "JME AutoMaterial"
    bl_idname = "JME_TOOLS_PT_automaterial_panel"
    bl_context = "material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    COMPAT_ENGINES = {'BLENDER_EEVEE', 'CYCLES'}

    def draw(self, context):
        # Button
        self.layout.operator("jmetools.automaterialpbr", text="Load PBR material")


def register():
    bpy.utils.register_class(JME_TOOLS_automaterial_PBR)
    bpy.utils.register_class(JME_TOOLS_PT_automaterial_panel)


def unregister():
    bpy.utils.unregister_class(JME_TOOLS_automaterial_PBR)
    bpy.utils.unregister_class(JME_TOOLS_PT_automaterial_panel)
