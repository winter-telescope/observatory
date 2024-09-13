# requirements needing to be ported from winter_utils


Direct dependencies in winter_image_daemon.py:
- [x] focuslooop_winter.py
- [ ] winter_image
- [x] paths.DEFAULT_OUTPUT_DIR 
- [x] paths.MASTERBIAS_DIR

Dependencies in focusloop_winter:
- [x] quick_calibrate_images.py
    - subtract_dark
    - flat_correct
- [x] mask.py
    - make_mask
- [x] ldactools
     - get_table_from_ldac
- [x] paths
    - astrom_sex
    - astrom_param
    - astrom_filter
    - astrom_nnw
    - MASK_DIR
    - MASTERDARK_DIR
    - MASTERFLAT_DIR
    - DEFAULT_OUTPUT_DIR
- [x] io
    - get_focus_images_in_directory
