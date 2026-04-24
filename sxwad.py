import struct
import os
import sys
import zlib

def calculate_padding(current_length, alignment):
    return (alignment - (current_length % alignment)) % alignment

def extract_sxwad(file_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(file_path, 'rb') as f:
        version = struct.unpack('<I', f.read(4))[0]
        num_files = struct.unpack('<I', f.read(4))[0]
        data_offset = struct.unpack('<I', f.read(4))[0]
        f.read(4)

        print(f"SXWAD Version: {version} | Files: {num_files}")

        for i in range(num_files):
            decomp_len = struct.unpack('<i', f.read(4))[0]
            comp_len = struct.unpack('<I', f.read(4))[0]
            offset = struct.unpack('<I', f.read(4))[0]
            name_len = struct.unpack('<I', f.read(4))[0]
            
            filename = f.read(name_len).decode('latin-1')
            f.read(1)
            
            padding = calculate_padding(name_len + 1, 4)
            f.read(padding)

            save_pos = f.tell()

            f.seek(offset)
            raw_data = f.read(comp_len)
            
            if decomp_len != -1 and decomp_len != comp_len:
                try:
                    final_data = zlib.decompress(raw_data)
                except zlib.error:
                    print(f"Error decompressing {filename}, saving raw.")
                    final_data = raw_data
            else:
                final_data = raw_data

            clean_name = filename.replace('D:\\', '').replace('d:\\', '').replace('\\', os.sep)
            out_path = os.path.join(output_dir, clean_name)
            
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'wb') as out_file:
                out_file.write(final_data)

            print(f"Extracted: {clean_name}")
            f.seek(save_pos)

def recompile_sxwad(input_dir, output_file):
    all_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, input_dir).replace(os.sep, '\\')
            all_files.append((full_path, rel_path))

    dir_size = 0
    for _, rel_path in all_files:
        name_bytes = rel_path.encode('latin-1')
        name_len = len(name_bytes)
        dir_size += 16 + name_len + 1 + calculate_padding(name_len + 1, 4)

    data_start_offset = 16 + dir_size
    current_file_offset = data_start_offset
    
    directory_entries = []
    data_blobs = []

    print(f"Packing {len(all_files)} files...")
    for full_path, rel_path in all_files:
        with open(full_path, 'rb') as f:
            raw_data = f.read()
            decomp_size = len(raw_data)
            
            if decomp_size == 0:
                comp_data = b''
                comp_size = 0
                save_decomp_size = -1
            else:
                comp_data = zlib.compress(raw_data)
                comp_size = len(comp_data)
                
                if comp_size >= decomp_size:
                    comp_data = raw_data
                    comp_size = decomp_size
                    save_decomp_size = -1
                else:
                    save_decomp_size = decomp_size

            name_bytes = rel_path.encode('latin-1')
            name_len = len(name_bytes)
            
            entry_meta = struct.pack('<iIII', save_decomp_size, comp_size, current_file_offset, name_len)
            entry_name = name_bytes + b'\x00'
            entry_padding = b'\x00' * calculate_padding(name_len + 1, 4)
            
            directory_entries.append(entry_meta + entry_name + entry_padding)
            data_blobs.append(comp_data)
            
            current_file_offset += comp_size

    with open(output_file, 'wb') as out:
        out.write(struct.pack('<IIII', 1, len(all_files), 16, 0))
        
        for entry in directory_entries:
            out.write(entry)
            
        for blob in data_blobs:
            out.write(blob)

    print(f"Success! {output_file} created. Final size: {os.path.getsize(output_file)} bytes.")

if __name__ == "__main__":
    # Extract contents of SXWAD file: python sxwad.py extract file.sxwad
    # Pack folder contents into SXWAD file: python sxwad.py pack folder result.sxwad
    mode = sys.argv[1]
    if mode == "extract":
        extract_sxwad(sys.argv[2], "extracted_sxwad")
    elif mode == "pack":
        recompile_sxwad(sys.argv[2], sys.argv[3])
