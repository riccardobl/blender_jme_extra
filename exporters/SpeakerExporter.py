from .Exporter import Exporter
import bpy,os,shutil
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants

class SpeakerExporter(Exporter):
   
    def copySoundFile(self,src,topath):
        base_name=src.name
        ext="."+src.filepath.lower().split(".")[-1]
        if ext == "":
            ext="."+src.filepath_raw.lower().split(".")[-1]
        if ext == "":
            ext="."+src.name.lower().split(".")[-1]

        origin_file=bpy.path.abspath(src.filepath) 
        print("Base sound name",base_name,"assets path",topath)
        output_file=os.path.join(topath,"Sounds",base_name)+ext  
        print("Write sound in",output_file)

        output_parent=os.path.dirname(output_file)
            
        is_packed=src.packed_file

        
        if not os.path.exists(output_parent):
            os.makedirs(output_parent)
        
        if is_packed:
            print(base_name,"is packed inside the blend file. It will be extracted in",output_file)
            with open(output_file, 'wb') as f:
                f.write(src.packed_file.data)
        else:
            print(origin_file,"will be copied in",output_file)
            if origin_file != output_file:
                shutil.copyfile(origin_file, output_file)            
      
        return "Sounds/"+base_name+ext
        
    def exportToEmbeddedBufferView(self, src, export_settings):
        ext="."+src.filepath.lower().split(".")[-1]
        if ext == "":
            ext="."+src.filepath_raw.lower().split(".")[-1]
        if ext == "":
            ext="."+src.name.lower().split(".")[-1]

        origin_file=bpy.path.abspath(src.filepath) 
        is_packed=src.packed_file

        data=None
        if is_packed:
            data=src.packed_file.data
        else:
            with open(origin_file, 'rb') as f:
                data=f.read()
        
        buffer_view=gltf2_io_binary_data.BinaryData(data, gltf2_io_constants.BufferViewTarget.ARRAY_BUFFER),

        return buffer_view
      
        

    def exportFromNode( self,gltf2_node, ob, export_settings):
        try:
            if not ob.type=='SPEAKER':
                return

            # TODO: Support embedded sounds
            embed=False
            if not embed:
                path=self.copySoundFile(ob.data.sound,export_settings['gltf_filedirectory'])        
            else:
                buffer=self.exportToEmbeddedBufferView(ob.data.sound,export_settings)
                # ???
                        
            ext = {
                "volume": ob.data.volume,
                "pitch": ob.data.pitch,
                "attenuation": ob.data.attenuation,
                "distance_max": ob.data.distance_max,
                "distance_reference": ob.data.distance_reference,
                "volume_min": ob.data.volume_min,
                "volume_max": ob.data.volume_max,
                "angle_outer_cone": ob.data.cone_angle_outer,
                "angle_inner_cone": ob.data. cone_angle_inner,
                "outer_cone_volume": ob.data.cone_volume_outer,
                "sound_path": path
            }

            gltf2_node.extensions['JME_speaker'] = ext

        except Exception as e:
            print("Error exporting speaker",e)
            raise e


        
