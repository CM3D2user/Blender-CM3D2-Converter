import bpy, mathutils
import struct, re, math, unicodedata
from . import common

# メインオペレーター
class export_cm3d2_anm(bpy.types.Operator):
	bl_idname = 'export_anim.export_cm3d2_anm'
	bl_label = "CM3D2モーション (.anm)"
	bl_description = "カスタムメイド3D2のanmファイルを保存します"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".anm"
	filter_glob = bpy.props.StringProperty(default="*.anm", options={'HIDDEN'})
	
	scale = bpy.props.FloatProperty(name="倍率", default=0.2, min=0.1, max=100, soft_min=0.1, soft_max=100, step=100, precision=1, description="エクスポート時のメッシュ等の拡大率です")
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	
	frame_start = bpy.props.IntProperty(name="開始フレーム", default=0, min=0, max=99999, soft_min=0, soft_max=99999, step=1)
	frame_end = bpy.props.IntProperty(name="最終フレーム", default=0, min=0, max=99999, soft_min=0, soft_max=99999, step=1)
	key_frame_count = bpy.props.IntProperty(name="キーフレーム数", default=1, min=1, max=99999, soft_min=1, soft_max=99999, step=1)
	time_scale = bpy.props.FloatProperty(name="再生速度", default=1.0, min=0.1, max=10.0, soft_min=0.1, soft_max=10.0, step=10, precision=1)
	is_keyframe_clean = bpy.props.BoolProperty(name="同じ変形のキーフレームを掃除", default=True)
	is_smooth_handle = bpy.props.BoolProperty(name="キーフレーム間の変形をスムーズに", default=False)
	
	is_remove_alone_bone = bpy.props.BoolProperty(name="親も子も存在しない", default=True)
	is_remove_ik_bone = bpy.props.BoolProperty(name="名前がIKっぽい", default=True)
	is_remove_serial_number_bone = bpy.props.BoolProperty(name="名前が連番付き", default=True)
	is_remove_japanese_bone = bpy.props.BoolProperty(name="名前に日本語が含まれる", default=True)
	
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
			self.filepath = common.default_cm3d2_dir(common.preferences().anm_export_path, "", "anm")
		self.frame_start = context.scene.frame_start
		self.frame_end = context.scene.frame_end
		self.scale = 1.0 / common.preferences().scale
		self.is_backup = bool(common.preferences().backup_ext)
		self.key_frame_count = (context.scene.frame_end - context.scene.frame_start) + 1
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'scale')
		
		box = self.layout.box()
		box.prop(self, 'is_backup', icon='FILE_BACKUP')
		box.prop(self, 'version')
		
		box = self.layout.box()
		sub_box = box.box()
		row = sub_box.row()
		row.prop(self, 'frame_start')
		row.prop(self, 'frame_end')
		sub_box.prop(self, 'key_frame_count')
		sub_box.prop(self, 'time_scale')
		sub_box.prop(self, 'is_keyframe_clean', icon='DISCLOSURE_TRI_DOWN')
		#sub_box.prop(self, 'is_smooth_handle', icon='SMOOTHCURVE')
		
		sub_box = box.box()
		sub_box.label("除外するボーン", icon='X')
		column = sub_box.column(align=True)
		column.prop(self, 'is_remove_alone_bone', icon='UNLINKED')
		column.prop(self, 'is_remove_ik_bone', icon='CONSTRAINT_BONE')
		column.prop(self, 'is_remove_serial_number_bone', icon='DOTSDOWN')
		column.prop(self, 'is_remove_japanese_bone', icon='MATCAP_13')
	
	def execute(self, context):
		common.preferences().anm_export_path = self.filepath
		
		try:
			file = common.open_temporary(self.filepath, 'wb', is_backup=self.is_backup)
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可の可能性があります")
			return {'CANCELLED'}
		
		try:
			with file:
				self.write_animation(context, file)
		except common.CM3D2ExportException as e:
			self.report(type={'ERROR'}, message=str(e))
			return {'CANCELLED'}
		
		return {'FINISHED'}
		
	def write_animation(self, context, file):
		ob = context.active_object
		arm = ob.data
		pose = ob.pose
		fps = context.scene.render.fps
		
		common.write_str(file, 'CM3D2_ANIM')
		file.write(struct.pack('<i', self.version))
		
		def is_japanese(string):
			for ch in string:
					name = unicodedata.name(ch) 
					if "CJK UNIFIED" in name \
					or "HIRAGANA" in name \
					or "KATAKANA" in name:
						return True
			return False
		bones = []
		already_bone_names = []
		bones_queue = arm.bones[:]
		while len(bones_queue):
			bone = bones_queue.pop(0)
			
			already_bone_names.append(bone.name)
			if self.is_remove_serial_number_bone:
				if re.search(r"\.\d{3,}$", bone.name): continue
			if self.is_remove_japanese_bone:
				if is_japanese(bone.name): continue
			
			if not bone.parent:
				if self.is_remove_alone_bone and len(bone.children) == 0:
					continue
				bones.append(bone)
				continue
			elif bone.parent.name in already_bone_names:
				if self.is_remove_ik_bone:
					if "_ik_" in bone.name.lower(): continue
					if re.search(r"_nub$", bone.name.lower()): continue
					if re.search(r"Nub$", bone.name): continue
				bones.append(bone)
				continue
			
			bones_queue.append(bone)
		
		anm_data_raw = {}
		class KeyFrame:
			def __init__(self, time, value):
				self.time = time
				self.value = value
		same_locs = {}
		same_rots = {}
		pre_rots = {}
		for key_frame_index in range(self.key_frame_count):
			if self.key_frame_count == 1:
				frame = 0.0
			else:
				frame = (self.frame_end - self.frame_start) / (self.key_frame_count - 1) * key_frame_index + self.frame_start
			context.scene.frame_set(int(frame), frame - int(frame))
			context.scene.update()
			
			time = frame / fps * (1.0 / self.time_scale)
			
			for bone in bones:
				if bone.name not in anm_data_raw:
					anm_data_raw[bone.name] = {"LOC":{}, "ROT":{}}
					same_locs[bone.name] = []
					same_rots[bone.name] = []
				
				pose_bone = pose.bones[bone.name]
				
				pose_mat = ob.convert_space(pose_bone, pose_bone.matrix, 'POSE', 'WORLD')
				if bone.parent:
					parent_mat = ob.convert_space(pose_bone.parent, pose_bone.parent.matrix, 'POSE', 'WORLD')
					pose_mat = parent_mat.inverted() * pose_mat
					#rot = pose_bone.parent.matrix.to_quaternion().rotation_difference(pose_bone.matrix.to_quaternion())
				
				loc = pose_mat.to_translation() * self.scale
				rot = pose_mat.to_quaternion()
				
				if bone.name in pre_rots:
					if 5.0 < pre_rots[bone.name].rotation_difference(rot).angle:
						rot.w, rot.x, rot.y, rot.z = -rot.w, -rot.x, -rot.y, -rot.z
				pre_rots[bone.name] = rot.copy()
				
				if bone.parent:
					loc.x, loc.y, loc.z = -loc.y, -loc.x, loc.z
					rot.w, rot.x, rot.y, rot.z = rot.w, rot.y, rot.x, -rot.z
				else:
					loc.x, loc.y, loc.z = -loc.x, loc.z, -loc.y
					
					fix_quat = mathutils.Euler((0, 0, math.radians(-90)), 'XYZ').to_quaternion()
					fix_quat2 = mathutils.Euler((math.radians(-90), 0, 0), 'XYZ').to_quaternion()
					rot = rot * fix_quat * fix_quat2
					
					rot.w, rot.x, rot.y, rot.z = -rot.y, -rot.z, -rot.x, rot.w
				
				if not self.is_keyframe_clean or int(frame) == self.frame_start or int(frame) == self.frame_end:
					anm_data_raw[bone.name]["LOC"][time] = loc.copy()
					anm_data_raw[bone.name]["ROT"][time] = rot.copy()
					
					if self.is_keyframe_clean:
						same_locs[bone.name].append(KeyFrame(time, loc.copy()))
						same_rots[bone.name].append(KeyFrame(time, rot.copy()))
				else:
					diff_length = (loc - same_locs[bone.name][-1].value).length
					if 0.0001 < diff_length:
						if 2 <= len(same_locs[bone.name]):
							anm_data_raw[bone.name]["LOC"][same_locs[bone.name][-1].time] = same_locs[bone.name][-1].value.copy()
						anm_data_raw[bone.name]["LOC"][time] = loc.copy()
						same_locs[bone.name] = [KeyFrame(time, loc.copy())]
					else:
						same_locs[bone.name].append(KeyFrame(time, loc.copy()))
					
					diff_angle = rot.rotation_difference(same_rots[bone.name][-1].value).angle
					if 0.0001 < diff_angle:
						if 2 <= len(same_rots[bone.name]):
							anm_data_raw[bone.name]["ROT"][same_rots[bone.name][-1].time] = same_rots[bone.name][-1].value.copy()
						anm_data_raw[bone.name]["ROT"][time] = rot.copy()
						same_rots[bone.name] = [KeyFrame(time, rot.copy())]
					else:
						same_rots[bone.name].append(KeyFrame(time, rot.copy()))
		
		anm_data = {}
		for bone_name, channels in anm_data_raw.items():
			anm_data[bone_name] = {100:{}, 101:{}, 102:{}, 103:{}, 104:{}, 105:{}, 106:{}}
			for time, loc in channels["LOC"].items():
				anm_data[bone_name][104][time] = loc.x
				anm_data[bone_name][105][time] = loc.y
				anm_data[bone_name][106][time] = loc.z
			for time, rot in channels["ROT"].items():
				anm_data[bone_name][100][time] = rot.x
				anm_data[bone_name][101][time] = rot.y
				anm_data[bone_name][102][time] = rot.z
				anm_data[bone_name][103][time] = rot.w
		
		for bone in bones:
			file.write(struct.pack('<?', True))
			
			bone_names = [bone.name]
			current_bone = bone
			while current_bone.parent:
				bone_names.append(current_bone.parent.name)
				current_bone = current_bone.parent
			
			bone_names.reverse()
			common.write_str(file, "/".join(bone_names))
			
			for channel_id, keyframes in sorted(anm_data[bone.name].items(), key=lambda x: x[0]):
				file.write(struct.pack('<B', channel_id))
				file.write(struct.pack('<i', len(keyframes)))
				
				keyframes_list = sorted(keyframes.items(), key=lambda x: x[0])
				for i in range(len(keyframes_list)):
					x = keyframes_list[i][0]
					y = keyframes_list[i][1]
					
					if len(keyframes_list) <= 1:
						file.write(struct.pack('<f', x))
						file.write(struct.pack('<f', y))
						file.write(struct.pack('<2f', 0.0, 0.0))
						continue
					
					if i == 0:
						prev_x = x - (keyframes_list[i+1][0] - x)
						prev_y = y - (keyframes_list[i+1][1] - y)
						next_x = keyframes_list[i+1][0]
						next_y = keyframes_list[i+1][1]
					elif i == len(keyframes_list) - 1:
						prev_x = keyframes_list[i-1][0]
						prev_y = keyframes_list[i-1][1]
						next_x = x + (x - keyframes_list[i-1][0])
						next_y = y + (y - keyframes_list[i-1][1])
					else:
						prev_x = keyframes_list[i-1][0]
						prev_y = keyframes_list[i-1][1]
						next_x = keyframes_list[i+1][0]
						next_y = keyframes_list[i+1][1]
					
					prev_rad = math.atan2((prev_y - y) * (fps / 4.0), prev_x - x)
					if math.pi / 2 < prev_rad:
						prev_rad -= math.pi
					elif prev_rad < math.pi / -2:
						prev_rad += math.pi
					next_rad = math.atan2((next_y - y) * (fps / 4.0), next_x - x)
					
					join_rad = (prev_rad + next_rad) / 2
					
					file.write(struct.pack('<f', x))
					file.write(struct.pack('<f', y))
					
					if self.is_smooth_handle:
						file.write(struct.pack('<2f', join_rad, join_rad))
					else:
						file.write(struct.pack('<2f', 0.0, 0.0))
		
		file.write(struct.pack('<?', False))

# メニューに登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_anm.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
