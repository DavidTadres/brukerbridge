import brukerbridge as bridge

extensions_for_oak_transfer = ['.nii', '.csv', '.xml', 'json', 'hdf5'] # last 4 chars

### Directory on this computer to process ###
# full_target = 'G:/Ashley/20210702'
# full_target = 'G:/Max/20220301'
# full_target = 'F:/Michelle/210805'
# full_target = 'H:/Tim/20220308'
full_target = 'H:/luke/20220324__queue__'
# full_target = 'H:/Minseung/visualattention'

### Oak target ###
# oak_target = 'X:/data/Brezovec/2P_Imaging/imports'
#oak_target = 'X:/data/Ashley2/imports'
# oak_target = 'X:/data/Max/ImagingData/Bruker/imports'
#oak_target = 'X/data/Ina/bruker_data/imports'
#oak_target = X:/data/Avery/bruker_data/imports'
# oak_target = 'X:/data/Michelle/Bruker/imports'
#oak_target = 'X:/data/Tim/ImagingData/imports'
oak_target = 'X:/data/Brezovec/2P_Imaging/imports'
# oak_target = 'X:/data/minseung/bruker_data/imports'

### raw to tiff ###
# bridge.convert_raw_to_tiff(full_target)

### tiffs to nii or tiff stack ###
#bridge.convert_tiff_collections_to_nii(full_target)
#bridge.convert_tiff_collections_to_stack(full_target)

### Transfer fictrac ###
user = 'luke'
bridge.transfer_fictrac(user)

### Transfer to oak ###
#bridge.start_oak_transfer(full_target, oak_target, extensions_for_oak_transfer, add_to_build_que="False")
