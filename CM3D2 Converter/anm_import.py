import os, re, bpy, math, struct, os.path, mathutils
from . import common

# メインオペレーター
class import_cm3d2_anm(bpy.types.Operator):
	bl_idname = 'import_mesh.import_cm3d2_anm'
	bl_label = "CM3D2モーション (.anm)"
	bl_description = "カスタムメイド3D2のanmファイルを読み込みます"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".anm"
	filter_glob = bpy.props.StringProperty(default="*.anm", options={'HIDDEN'})
	
	scale = bpy.props.FloatProperty(name="倍率", default=5, min=0.1, max=100, soft_min=0.1, soft_max=100, step=100, precision=1, description="インポート時のメッシュ等の拡大率です")
	
	remove_pre_animation = bpy.props.BoolProperty(name="既にあるアニメーションを削除", default=True)
	
	is_location = bpy.props.BoolProperty(name="位置", default=True)
	is_rotation = bpy.props.BoolProperty(name="回転", default=True)
	is_scale = bpy.props.BoolProperty(name="拡大/縮小", default=False)
	
	set_frame = bpy.props.BoolProperty(name="Blenderのフレーム設定を調整", default=True)
	
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
		self.scale = common.preferences().scale
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'scale')
		self.layout.prop(self, 'remove_pre_animation', icon='DISCLOSURE_TRI_DOWN')
		box = self.layout.box()
		box.label("読み込むアニメーション情報")
		box.prop(self, 'is_location', icon='MAN_TRANS')
		box.prop(self, 'is_rotation', icon='MAN_ROT')
		row = box.row()
		row.prop(self, 'is_scale', icon='MAN_SCALE')
		row.enabled = False
		self.layout.prop(self, 'set_frame', icon='NEXT_KEYFRAME')
	
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
			if base_bone_name not in anm_data:
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
		
		if self.remove_pre_animation:
			anim = ob.animation_data
			if anim:
				for fcurve in anim.action.fcurves:
					anim.action.fcurves.remove(fcurve)
		
		max_frame = 0
		bpy.ops.object.mode_set(mode='OBJECT')
		for bone_name, bone_data in anm_data.items():
			if bone_name not in pose.bones:
				bone_name = common.decode_bone_name(bone_name)
				if bone_name not in pose.bones:
					continue
			bone = arm.bones[bone_name]
			pose_bone = pose.bones[bone_name]
			
			locs = {}
			quats = {}
			for channel_id, channel_data in bone_data['channels'].items():
				
				if channel_id in [100, 101, 102, 103]:
					for data in channel_data:
						frame = data['frame']
						if frame not in quats:
							quats[frame] = [None, None, None, None]
						
						if channel_id == 103:
							quats[frame][0] = -data['f0']
						elif channel_id == 100:
							quats[frame][1] = -data['f0']
						elif channel_id == 102:
							quats[frame][2] = -data['f0']
						elif channel_id == 101:
							quats[frame][3] = data['f0']
				
				elif channel_id in [104, 105, 106]:
					for data in channel_data:
						frame = data['frame']
						if frame not in locs:
							locs[frame] = [None, None, None]
						
						if channel_id == 104:
							locs[frame][0] = -data['f0']
						elif channel_id == 106:
							locs[frame][1] = -data['f0']
						elif channel_id == 105:
							locs[frame][2] = data['f0']
			
			if self.is_rotation:
				for frame, quat in quats.items():
					quat = mathutils.Quaternion(quat)
					
					q = mathutils.Quaternion((0, 0, 1), math.radians(90))
					bone_quat = bone.matrix_local.to_quaternion()
					bone_quat = bone_quat * q
					if bone.parent:
						parent_quat = bone.parent.matrix_local.to_quaternion()
						parent_quat = parent_quat * q
						bone_quat = parent_quat.rotation_difference(bone_quat)
					
					pose_quat = bone_quat.rotation_difference(quat)
					pose_quat.w, pose_quat.x, pose_quat.y, pose_quat.z = pose_quat.w, -pose_quat.y, pose_quat.x, pose_quat.z
					pose_bone.rotation_quaternion = pose_quat
					
					pose_bone.keyframe_insert('rotation_quaternion', frame=frame * fps)
					if max_frame < frame * fps:
						max_frame = frame * fps
			
			if self.is_location:
				for frame, loc in locs.items():
					loc = mathutils.Vector(loc) * self.scale
					
					bone_loc = bone.head_local.copy()
					if bone.parent:
						parent_loc = bone.parent.head_local.copy()
						bone_loc = bone_loc - parent_loc
						
						quat = bone.parent.matrix_local.to_quaternion()
						quat.invert()
						bone_loc.rotate(quat)
						bone_loc.x, bone_loc.y, bone_loc.z = bone_loc.y, -bone_loc.x, bone_loc.z
					
					pose_loc = loc - bone_loc
					bone_quat = bone.matrix_local.to_quaternion()
					pose_loc.rotate(bone_quat)
					
					pose_bone.location = pose_loc
					pose_bone.keyframe_insert('location', frame=frame * fps)
					if max_frame < frame * fps:
						max_frame = frame * fps
		
		if self.set_frame:
			context.scene.frame_end = max_frame
			context.scene.frame_current = 0
		
		return {'FINISHED'}

# メニューに登録する関数
def menu_func(self, context):
	self.layout.operator(import_cm3d2_anm.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
