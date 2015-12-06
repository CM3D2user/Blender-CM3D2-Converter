import os, os.path, bpy, struct, os.path
from . import common

class import_cm3d2_tex(bpy.types.Operator):
	bl_idname = 'image.import_cm3d2_tex'
	bl_label = "texファイルを開く"
	bl_description = "CM3D2で使用されるテクスチャファイル(.tex)を読み込みます"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".tex;.png"
	filter_glob = bpy.props.StringProperty(default="*.tex;*.png", options={'HIDDEN'})
	
	items = [
		('PACK', "内部にパックする", "", 1),
		('PNG', "PNGに変換してPNGを開く", "", 2),
		]
	mode = bpy.props.EnumProperty(items=items, name="展開方法", default='PNG')
	
	def invoke(self, context, event):
		if common.preferences().tex_default_path:
			self.filepath = common.default_cm3d2_dir(common.preferences().tex_default_path, "", "tex")
		else:
			self.filepath = common.default_cm3d2_dir(common.preferences().tex_import_path, "", "tex")
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'mode', icon='FILESEL')
	
	def execute(self, context):
		common.preferences().tex_import_path = self.filepath
		try:
			file = open(self.filepath, 'rb')
		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可かファイルが存在しません")
			return {'CANCELLED'}
		header_ext = common.read_str(file)
		if header_ext == 'CM3D2_TEX':
			file.seek(4, 1)
			in_path = common.read_str(file)
			png_size = struct.unpack('<i', file.read(4))[0]
			root, ext = os.path.splitext(self.filepath)
			png_path = root + ".png"
			is_png_overwrite = os.path.exists(png_path)
			if self.mode == 'PACK' and is_png_overwrite:
				png_path += ".temp.png"
			png_file = open(png_path, 'wb')
			png_file.write(file.read(png_size))
			png_file.close()
			bpy.ops.image.open(filepath=png_path)
			img = context.edit_image
			img.name = os.path.basename(self.filepath)
			img['cm3d2_path'] = in_path
		else:
			bpy.ops.image.open(filepath=self.filepath)
			img = context.edit_image
		file.close()
		if self.mode == 'PACK':
			img.pack(as_png=True)
			if header_ext == 'CM3D2_TEX':
				os.remove(png_path)
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.separator()
	self.layout.operator(import_cm3d2_tex.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
