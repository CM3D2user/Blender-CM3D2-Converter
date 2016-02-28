import os, re, bpy, math, struct, os.path, mathutils
from . import common

# メインオペレーター
class export_cm3d2_anm(bpy.types.Operator):
	bl_idname = 'export_anim.export_cm3d2_anm'
	bl_label = "CM3D2モーション (.anm) (開発中)"
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
		
		ob = context.active_object
		arm = ob.data
		
		# バックアップ
		common.file_backup(self.filepath, self.is_backup)
		
		try:
			file = open(self.filepath, 'wb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可かファイルが存在しません")
			return {'CANCELLED'}
		
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
		
		for bone in bones:
			file.write(struct.pack('<?', True))
			
			bone_names = [bone.name]
			current_bone = bone
			while current_bone.parent:
				bone_names.append(current_bone.parent.name)
				current_bone = current_bone.parent
			
			bone_names.reverse()
			common.write_str(file, "/".join(bone_names))
		
		file.write(struct.pack('<?', False))
		file.close()
		
		return {'FINISHED'}

# メニューに登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_anm.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
