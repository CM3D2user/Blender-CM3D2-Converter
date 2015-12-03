import os, re, bpy, struct, os.path, shutil
from . import common

class export_cm3d2_tex(bpy.types.Operator):
	bl_idname = 'image.export_cm3d2_tex'
	bl_label = "texファイルを保存"
	bl_description = "CM3D2で使用されるテクスチャファイル(.tex)として保存します"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".tex"
	filter_glob = bpy.props.StringProperty(default="*.tex", options={'HIDDEN'})
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	path = bpy.props.StringProperty(name="パス", default="assets/texture/texture/*.png")
	
	@classmethod
	def poll(cls, context):
		img = context.edit_image
		if img:
			if len(img.pixels):
				return True
		return False
	
	def invoke(self, context, event):
		img = context.edit_image
		if img.filepath:
			common.preferences().tex_export_path = img.filepath
		if common.preferences().tex_default_path:
			self.filepath = common.default_cm3d2_dir(common.preferences().tex_default_path, common.remove_serial_number(img.name), "tex")
		else:
			self.filepath = common.default_cm3d2_dir(common.preferences().tex_export_path, common.remove_serial_number(img.name), "tex")
		self.is_backup = bool(common.preferences().backup_ext)
		if 'cm3d2_path' in img.keys():
			self.path = img['cm3d2_path']
		else:
			self.path = "assets/texture/texture/" + os.path.basename(self.filepath)
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not common.preferences().backup_ext:
			row.enabled = False
		self.layout.prop(self, 'version', icon='LINENUMBERS_ON')
		self.layout.prop(self, 'path', icon='ANIM')
	
	def execute(self, context):
		common.preferences().tex_export_path = self.filepath
		
		# バックアップ
		common.file_backup(self.filepath, self.is_backup)
		
		temp_path = self.filepath + ".temp.png"
		
		# とりあえずpngで保存
		img = context.edit_image
		pre_filepath = img.filepath
		pre_source = img.source
		bpy.ops.image.save_as(save_as_render=False, filepath=temp_path, relative_path=True, show_multiview=False, use_multiview=False)
		img.filepath = pre_filepath
		img.source = pre_source
		
		# pngバイナリを全て読み込み
		temp_file = open(temp_path, 'rb')
		temp_data = temp_file.read()
		temp_file.close()
		# 一時ファイルを削除
		os.remove(temp_path)
		
		# 本命ファイルに書き込み
		try:
			file = open(self.filepath, 'wb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可の可能性があります")
			return {'CANCELLED'}
		common.write_str(file, 'CM3D2_TEX')
		file.write(struct.pack('<i', self.version))
		common.write_str(file, self.path)
		file.write(struct.pack('<i', len(temp_data)))
		file.write(temp_data)
		file.close()
		
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_tex.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
