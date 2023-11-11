
from .tools import AutoMaterial

bl_info = {
    "name" : "JMonkeyEngine Extra",
    "author" : "Riccardo Balbo",
    "version": (1,0,0),
    "description" : "",
    "blender" : (3,6, 0),
    "location" : "",
    "warning" : "",
    "category" : "Import-Export"
}

 
def register():
    print("Registered")
    AutoMaterial.register()


def unregister():
    print("Unregistered")
    AutoMaterial.unregister()
 

class glTF2ExportUserExtension:
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension=Extension
        self.exps=None

    def getExps(self):
        if not self.exps:
            self.exps=[]
            from .exporters.RigidBodyExporter import RigidBodyExporter
            self.exps.append(RigidBodyExporter())

            from .exporters.SpeakerExporter import SpeakerExporter
            self.exps.append(SpeakerExporter())

            from .exporters.PropertiesAnimationExporter import PropertiesAnimationExporter
            self.exps.append(PropertiesAnimationExporter())
        return self.exps



    def gather_node_hook(self, gltf2_node, blender_object, export_settings):
        print("gather_node_hook")
        for e in self.getExps():
            e.exportFromNode(gltf2_node, blender_object, export_settings)
