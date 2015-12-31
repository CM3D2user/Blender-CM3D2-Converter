import os, re, bpy, math, struct, os.path, mathutils
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
		if common.preferences().anm_default_path:
			self.filepath = common.default_cm3d2_dir(common.preferences().anm_default_path, "", "anm")
		else:
			self.filepath = common.default_cm3d2_dir(common.preferences().anm_import_path, "", "anm")
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		pass
	
	def execute(self, context):
		common.preferences().anm_import_path = self.filepath
		
		try:
			file = open(self.filepath, 'rb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可かファイルが存在しません")
			return {'CANCELLED'}
		
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
				channel_id_str = channel_id
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
			
			quats = {}
			for channel_id, channel_data in bone_data['channels'].items():
				
				if channel_id not in [100, 101, 102, 103]:
					continue
				
				for data in channel_data:
					
					frame = data['frame']
					if frame not in quats.keys():
						quats[frame] = [None, None, None, None]
					
					if channel_id == 103:
						quats[frame][0] = data['f0']
					elif channel_id == 100:
						quats[frame][1] = -data['f0']
					elif channel_id == 102:
						quats[frame][2] = -data['f0']
					elif channel_id == 101:
						quats[frame][3] = data['f0']
			
			for frame, quat in quats.items():
				quat = mathutils.Quaternion(quat)
				#eul = mathutils.Euler((math.radians(-90), 0, 0), 'XYZ')
				#quat.rotate(eul)
				
				#bone_quat = arm.bones[bone_name].matrix.to_quaternion()
				#quat = quat * bone_quat
				
				print(bone_name)
				print(quat)
				eul = quat.to_euler()
				print( int(math.degrees(eul[0])), int(math.degrees(eul[1])), int(math.degrees(eul[2])) )
				
				pose_bone.rotation_quaternion = eul.to_quaternion().copy()
				
				pose_bone.keyframe_insert('rotation_quaternion', frame=frame * fps)
		
		return {'FINISHED'}

# メニューに登録する関数
def menu_func(self, context):
	self.layout.operator(import_cm3d2_anm.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
