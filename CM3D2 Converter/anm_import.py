import os, re, bpy, struct, os.path
from . import common

# メインオペレーター
class import_cm3d2_anm(bpy.types.Operator):
	bl_idname = 'import_mesh.import_cm3d2_anm'
	bl_label = "(開発中) CM3D2 Motion (.anm)"
	bl_description = "カスタムメイド3D2のanmファイルを読み込みます"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".anm"
	filter_glob = bpy.props.StringProperty(default="*.anm", options={'HIDDEN'})
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				return True
		return False
	
	def invoke(self, context, event):
		self.filepath = common.default_cm3d2_dir(context.user_preferences.addons[__name__.split('.')[0]].preferences.anm_import_path, "", "anm")
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		pass
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.anm_import_path = self.filepath
		
		file = open(self.filepath, 'rb')
		
		# ヘッダー
		ext = common.read_str(file)
		if ext != 'CM3D2_ANIM':
			self.report(type={'ERROR'}, message="これはカスタムメイド3D2のモーションファイルではありません")
			return {'CANCELLED'}
		struct.unpack('<i', file.read(4))[0]
		
		global_flag = struct.unpack('<?', file.read(1))[0]
		
		anm_data = {}
		
		for anm_data_index in range(9**9):
			path = common.read_str(file)
			
			base_bone_name = path.split('/')[-1]
			if base_bone_name not in anm_data.keys():
				anm_data[base_bone_name] = {'path':path}
				anm_data[base_bone_name]['channels'] = {}
			
			for channel_index in range(9**9):
				channel_id = struct.unpack('<B', file.read(1))[0]
				channel_id_str = str(channel_id)
				if channel_id <= 1:
					break
				anm_data[base_bone_name]['channels'][channel_id_str] = []
				channel_data_count = struct.unpack('<i', file.read(4))[0]
				for channel_data_index in range(channel_data_count):
					frame = struct.unpack('<f', file.read(4))[0]
					data = struct.unpack('<3f', file.read(4*3))
					
					anm_data[base_bone_name]['channels'][channel_id_str].append({'frame':frame, 'f0':data[0], 'f1':data[1], 'f2':data[2]})
			
			if channel_id == 0:
				break
		
		fps = context.scene.render.fps
		
		ob = context.active_object
		arm = ob.data
		pose = ob.pose
		
		bpy.ops.object.mode_set(mode='EDIT')
		for edit_bone in arm.edit_bones:
			edit_bone.use_connect = False
		for edit_bone in arm.edit_bones:
			head_co = edit_bone.head.copy()
			head_co.z += 0.5
			edit_bone.tail = head_co
			edit_bone.roll = 0.0
		
		bpy.ops.object.mode_set(mode='OBJECT')
		for bone_name, bone_data in anm_data.items():
			if bone_name not in pose.bones.keys():
				bone_name = common.decode_bone_name(bone_name)
				if bone_name not in pose.bones.keys():
					continue
			pose_bone = pose.bones[bone_name]
			
			for channel_id, channel_data in bone_data['channels'].items():
				
				data_path = 'rotation_quaternion'
				data_index = -1
				if channel_id == '100':
					data_index = 1
				elif channel_id == '101':
					data_index = 2
				elif channel_id == '102':
					data_index = 3
				elif channel_id == '103':
					data_index = 0
				else:
					continue
				
				for data in channel_data:
					frame = data['frame']
					
					if channel_id == '100':
						pose_bone.rotation_quaternion[data_index] = data['f0']
					elif channel_id == '101':
						pose_bone.rotation_quaternion[data_index] = data['f0']
					elif channel_id == '102':
						pose_bone.rotation_quaternion[data_index] = data['f0']
					elif channel_id == '103':
						pose_bone.rotation_quaternion[data_index] = data['f0']
					
					pose_bone.keyframe_insert(data_path, index=data_index, frame=frame * fps)
		
		return {'FINISHED'}

# メニューに登録する関数
def menu_func(self, context):
	self.layout.operator(import_cm3d2_anm.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
