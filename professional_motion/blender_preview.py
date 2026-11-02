"""Optional isolated Blender lighting preview of exact exported Three.js geometry.

This command does not create narration, submit posts, or claim a complete film.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('glb');p.add_argument('output');p.add_argument('--resolution',type=int,default=640)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if not 320<=a.resolution<=1920:raise ValueError('Bounded portrait preview height required')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(Path(a.glb).resolve()))
report=json.loads(Path(a.glb+'.json').read_text());view=report['view']
def converted(point):return Vector((point[0],-point[2],point[1]))
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));bpy.context.scene.collection.objects.link(camera);camera.location=converted(view['position']);camera.rotation_euler=(converted(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=50;camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=36;bpy.context.scene.camera=camera
for name,position,power,size,color in [('Key',(4,-6,7),1000,5,(.8,.93,1)),('Fill',(-4,-3,4),650,5,(.52,.8,1)),('Rim',(2,4,6),1200,4,(1,.67,.4))]:
 light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));bpy.context.scene.collection.objects.link(light);light.location=position;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.data.color=color
scene=bpy.context.scene;scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.018,.035,.05,1)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=False;scene.render.resolution_x=round(a.resolution*9/16);scene.render.resolution_y=a.resolution;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(Path(a.output).resolve());bpy.ops.render.render(write_still=True)
Path(a.output+'.json').write_text(json.dumps({**report,'engine':'Blender Cycles CPU','width':scene.render.resolution_x,'height':scene.render.resolution_y,'preview_only':True,'publishable':False},indent=2))
