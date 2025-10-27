import os
from reversebox.io_files.file_handler import FileHandler
from reversebox.compression.compression_zlib import ZLIBHandler
from reversebox.image.image_decoder import ImageDecoder
from reversebox.image.image_formats import ImageFormats
from reversebox.image import byte_swap
from reversebox.image.swizzling import swizzle_gamecube
from reversebox.image.pillow_wrapper import PillowWrapper
import reversebox.io_files.bytes_helper_functions as BytesHelper
import struct

TEXTURE_MAGIC_NUMBER = 0x29857294
zlib_handler = ZLIBHandler()
ENDIANESS = ">"
ENDIANESS_STR = "big"

def extract_texture(data:bytearray, file_name:str, pos: int = 0):
    cursor = pos
    magic_number = BytesHelper.get_uint32(data[cursor: cursor + 4], ENDIANESS)

    if magic_number != TEXTURE_MAGIC_NUMBER:
        raise Exception("Invalid file format")

    cursor+=8
    size = BytesHelper.get_uint32(data[cursor: cursor + 4], ENDIANESS)
    cursor+=8
    image_buffer_offset = BytesHelper.get_uint16(data[cursor: cursor + 2], ENDIANESS)
    cursor+=2
    image_palette_offset = BytesHelper.get_uint16(data[cursor: cursor + 2], ENDIANESS)
    cursor+=2
    width = BytesHelper.get_uint16(data[cursor: cursor + 2], ENDIANESS)
    cursor+=2
    height = BytesHelper.get_uint16(data[cursor: cursor + 2], ENDIANESS)
    cursor = pos

    decoder = ImageDecoder()
    wrapper = PillowWrapper()

    pil_image = None

    if image_buffer_offset == image_palette_offset and image_buffer_offset < size:
        # then its probably a dtx1 texture with GC byteswap

        image_data:bytes = data[cursor + image_buffer_offset: cursor + size]

        image_data = byte_swap.swap_byte_order_gamecube(image_data, width, height)

        converted_data: bytes = decoder.decode_compressed_image(image_data, width, height, ImageFormats.BC1_DXT1)
        pil_image = wrapper.get_pillow_image_from_rgba8888_data(converted_data, width, height)

    elif image_buffer_offset and image_buffer_offset < size:
        image_data:bytes = data[cursor + image_buffer_offset: cursor + size]

        image_data = swizzle_gamecube.unswizzle_gamecube(image_data, width, height, 8)
        converted_data: bytes = decoder.decode_image(image_data, width, height, ImageFormats.GRAY8)
        pil_image = wrapper.get_pillow_image_from_rgba8888_data(converted_data, width, height)

    if pil_image is None:
        return

    out_path = file_name + ".png"

    print(out_path)

    pil_image.save(out_path)


def find_textures(data:bytearray) -> list:
    positions = []

    pos = 0
    pos = data.find(struct.pack(f"{ENDIANESS}I",TEXTURE_MAGIC_NUMBER), pos)

    while pos != -1:
        positions.append(pos)
        pos = data.find(struct.pack(f"{ENDIANESS}I",TEXTURE_MAGIC_NUMBER), pos + 4)

    return positions

def pes_decompress(data:bytearray, pos:int = 0):
    """
    This function could be totally improved, but so far this was what worked just fine to extract
    """
    return zlib_handler.decompress_data(data[pos + 32:])

def extract_textures_from_folder(folder_path:str, filter_prefixes:tuple):
    for file in os.listdir(folder_path):
        if not file.endswith(filter_prefixes):
            continue

        file_path = os.path.join(folder_path, file)
        print(file_path)

        value = None
        file_reader = None
        try:
            file_reader = FileHandler(file_path=file_path, open_mode="rb", endianess_str=ENDIANESS_STR)
            value = file_reader.read_uint32()
        except Exception as e:
            print(e)
        
        if file_reader is None or file_reader.file is None:
            continue

        file_reader.file.seek(0)

        file_data = bytearray(file_reader.read_whole_file_content())

        file_reader.close()

        if value is None:
            continue

        if value == TEXTURE_MAGIC_NUMBER:
            extract_texture(file_data, f"{file_path}_{0:03d}", 0)
        elif (value >> 8 & 0xff) == 0x01:
            try:
                decompress_data = bytearray(pes_decompress(file_data))
                file_path += f"_{0:03d}"
                positions = find_textures(decompress_data)
                for i, position in enumerate(positions):
                    extract_texture(decompress_data, f"{file_path}_{i:03d}", position)
            except Exception as e:
                print(e)
def main():

    # # example to extract texture from a folder
    # # using specific prefix tuple to filter out files
    # folder_path = "D:/pes wii/0_text/"
    # filter_prefixes = tuple(".bin")
    # extract_textures_from_folder(folder_path, filter_prefixes=filter_prefixes)

    ## below there's a few other examples of test made by myself

    # file_path = "D:/pes wii/0_text/unknow_00000.bin_000" # ball decompress
    # file_path = "D:/pes wii/0_text/unknow_03102.bin_000" # face decompress
    # file_path = "D:/pes wii/0_text/unknow_07772.bin_000" # kit decompress
    # file_path = "D:/pes wii/0_text/unknow_00001.bin" # ball compress

    # with open(file_path, "rb") as f:
    #     data = bytearray(f.read())

    # decompress_data = bytearray(pes_decompress(data))

    # file_path += "_000"

    # positions = find_textures(decompress_data)

    # for i, position in enumerate(positions):
    #     extract_texture(decompress_data, f"{file_path}_{i:03d}", position)


    return


if __name__ == "__main__":
    main()

