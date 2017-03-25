import bpy, mathutils
import struct, re, math
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
		self.scale = 1.0 / common.preferences().scale
		self.is_backup = bool(common.preferences().backup_ext)
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'scale')
		self.layout.prop(self, 'is_backup')
		self.layout.prop(self, 'version')
	
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
		anim_data = ob.animation_data
		fps = context.scene.render.fps
		
		common.write_str(file, 'CM3D2_ANIM')
		file.write(struct.pack('<i', self.version))
		
		bones = []
		already_bone_names = []
		bones_que = arm.bones[:]
		while len(bones_que):
			bone = bones_que.pop(0)
			
			if not bone.parent:
				bones.append(bone)
				already_bone_names.append(bone.name)
				continue
			elif bone.parent.name in already_bone_names:
				bones.append(bone)
				already_bone_names.append(bone.name)
				continue
			
			bones_que.append(bone)
		
		raw_keyframe_data = {}
		if anim_data:
			if anim_data.action:
				for fcurve in anim_data.action.fcurves:
					if re.match(r'pose\.bones\["[^"\[\]]+"\]\.(location|rotation_quaternion)', fcurve.data_path):
						bone_name = re.search(r'pose\.bones\["([^"\[\]]+)"\]', fcurve.data_path).group(1)
						key_type = re.search(r'pose\.bones\["[^"\[\]]+"\]\.(location|rotation_quaternion)', fcurve.data_path).group(1)
						if bone_name not in raw_keyframe_data:
							raw_keyframe_data[bone_name] = {'location':{}, 'rotation_quaternion':{}}
						for keyframe in fcurve.keyframe_points:
							frame = keyframe.co.x / fps
							if frame not in raw_keyframe_data[bone_name][key_type]:
								if key_type == 'location':
									raw_keyframe_data[bone_name][key_type][frame] = mathutils.Vector()
								elif key_type == 'rotation_quaternion':
									raw_keyframe_data[bone_name][key_type][frame] = mathutils.Euler().to_quaternion()
							raw_keyframe_data[bone_name][key_type][frame][fcurve.array_index] = keyframe.co.y
		
		for bone in bones:
			if bone.name not in raw_keyframe_data:
				raw_keyframe_data[bone.name] = {'location':{}, 'rotation_quaternion':{}}
			if not len(raw_keyframe_data[bone.name]['location']):
				raw_keyframe_data[bone.name]['location'][0.0] = pose.bones[bone.name].location.copy()
			if not len(raw_keyframe_data[bone.name]['rotation_quaternion']):
				raw_keyframe_data[bone.name]['rotation_quaternion'][0.0] = pose.bones[bone.name].rotation_quaternion.copy()
		
		keyframe_data = {}
		for bone in bones:
			keyframe_data[bone.name] = {}
			if bone.name in raw_keyframe_data:
				for frame, loc in raw_keyframe_data[bone.name]['location'].items():
					
					bone_loc = bone.head_local.copy()
					if bone.parent:
						bone_loc = bone_loc - bone.parent.head_local
						bone_loc.rotate(bone.parent.matrix_local.to_quaternion().inverted())
					else:
						bone_loc.rotate(bone.matrix_local.to_quaternion().inverted())
					
					result_loc = bone_loc + loc
					result_loc.z, result_loc.x, result_loc.y = result_loc.x, -result_loc.y, result_loc.z
					result_loc = result_loc * self.scale
					
					if not bone.parent:
						result_loc.z, result_loc.x, result_loc.y = result_loc.x, result_loc.y, result_loc.z
					
					if 104 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][104] = {}
					keyframe_data[bone.name][104][frame] = result_loc.x
					
					if 105 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][105] = {}
					keyframe_data[bone.name][105][frame] = result_loc.y
					
					if 106 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][106] = {}
					keyframe_data[bone.name][106][frame] = result_loc.z
				
				for frame, quat in raw_keyframe_data[bone.name]['rotation_quaternion'].items():
					
					fix_quat = mathutils.Euler((math.radians(90), 0.0, 0.0), 'XYZ').to_quaternion()
					if not bone.parent:
						quat = fix_quat * quat
					
					bone_quat = bone.matrix.to_quaternion()
					result_quat = bone_quat * quat
					
					result_quat.w, result_quat.z, result_quat.x, result_quat.y = result_quat.w, -result_quat.x, result_quat.y, -result_quat.z
					
					if 100 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][100] = {}
					keyframe_data[bone.name][100][frame] = result_quat.x
					
					if 101 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][101] = {}
					keyframe_data[bone.name][101][frame] = result_quat.y
					
					if 102 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][102] = {}
					keyframe_data[bone.name][102][frame] = result_quat.z
					
					if 103 not in keyframe_data[bone.name]:
						keyframe_data[bone.name][103] = {}
					keyframe_data[bone.name][103][frame] = result_quat.w
		
		for bone in bones:
			file.write(struct.pack('<?', True))
			
			bone_names = [bone.name]
			current_bone = bone
			while current_bone.parent:
				bone_names.append(current_bone.parent.name)
				current_bone = current_bone.parent
			
			bone_names.reverse()
			common.write_str(file, "/".join(bone_names))
			
			for channel_id, keyframes in keyframe_data[bone.name].items():
				file.write(struct.pack('<B', channel_id))
				file.write(struct.pack('<i', len(keyframe_data[bone.name][channel_id])))
				for frame, value in keyframe_data[bone.name][channel_id].items():
					file.write(struct.pack('<f', frame))
					file.write(struct.pack('<f', value))
					file.write(struct.pack('<2f', 0.0, 0.0))
		
		file.write(struct.pack('<?', False))

# メニューに登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_anm.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
