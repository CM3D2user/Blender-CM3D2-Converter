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
		('PACK', "内部にパックする", "", 'PACKAGE', 1),
		('PNG', "PNGに変換してPNGを開く", "", 'IMAGE_DATA', 2),
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
		box = self.layout.box()
		col = box.column(align=True)
		col.label(text="展開方法", icon='FILESEL')
		col.prop(self, 'mode', icon='FILESEL', expand=True)
	
	def execute(self, context):
		common.preferences().tex_import_path = self.filepath
		try:
			tex_data = common.load_cm3d2tex(self.filepath)
			if tex_data is None:
				# bpy.ops.image.open(filepath=self.filepath)
				# img = context.edit_image
				self.report(type={'ERROR'}, message="texファイルのヘッダが正しくありません。" + self.fielpath)
				return {'CANCELLED'}

			tex_format = tex_data[1]
			if not (tex_format == 3 or tex_format == 5):
				self.report(type={'ERROR'}, message="未対応フォーマットのtexです。format=" + str(tex_format))
				return {'CANCELLED'}

			root, ext = os.path.splitext(self.filepath)
			png_path = root + ".png"
			is_png_overwrite = os.path.exists(png_path)
			if self.mode == 'PACK' and is_png_overwrite:
				png_path += ".temp.png"
			with open(png_path, 'wb') as png_file:
				png_file.write(tex_data[-1])
			bpy.ops.image.open(filepath=png_path)
			img = context.edit_image
			img.name = os.path.basename(self.filepath)
			img['cm3d2_path'] = in_path

			if self.mode == 'PACK':
				img.pack(as_png=True)
				os.remove(png_path)
			return {'FINISHED'}

		except:
			self.report(type={'ERROR'}, message="ファイルを開くのに失敗しました、アクセス不可かファイルが存在しません。"+ self.filepath)
			return {'CANCELLED'}


# メニューを登録する関数
def menu_func(self, context):
	self.layout.separator()
	self.layout.operator(import_cm3d2_tex.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
