GetData-0.10.0 introduces Dirfile Standards Version 10.  See below for details.
It also adds new functionality to the library and fixes bugs discovered since
the release of GetData-0.9.4.

The long-deprecated GetData-0.6 API has also been removed from this release.

---------------------------------------------------------------------------

Four packages are available:
* getdata-0.10.0.tar.bz2/.gz: the full source code to the library, with
    bindings.  This package uses the GNU autotools build system, and is
    designed for POSIX systems (UNIX, Linux, BSD, MacOS X, Cygwin, MSys,
    &c.)
* getdata_win-0.10.0.zip: a reduced source code package, with the CMake
    build system designed to be built on Microsoft Windows, either using
    the free MinGW compiler, or else Microsoft's Visual C++ compiler.
    (The full source package above can also be built using MinGW, if the
    MSys shell is used to run the build system.)  Currently, the only
    bindings provided by this package are the C++ bindings, and the
    package lacks support for compressed dirfiles, the Legacy API, and a
    few other features.  This build is used in native Microsoft Windows
    builds of kst2.
* idl_getdata-0.10.0.tar.bz2/.gz: the Interactive Data Language (IDL)
    bindings, packaged separately with an autotools build system, designed
    to be built against an already installed version of GetData.  Due to
    licensing restrictions, pre-built packages rarely come with these
    bindings, and this package allows end-users to add support for IDL
    without having to recompile the whole GetData package.
* matlab_getdata-0.10.0.tar.bz2/.gz: the MATLAB bindings, packaged
    separately with an autotools build system, designed to be built against
    an already installed version of GetData.  Due to licensing
    restrictions, pre-built packages rarely come with these bindings, and
    this package allows end- users to add support for MATLAB without having
    to recompile the whole GetData package.

---------------------------------------------------------------------------
New in version 0.10.0:

  Dirfile Changes:

  * Dirfile Standards Version 10 has been released.  It adds three new
    field types: SARRAY, which is an array of STRING scalars (like a
    CARRAY, but with STRINGs instead of CONSTs), and INDIR and SINDIR,
    which are vector fields provide indexed look-ups from CARRAY (INDIR) or
    SARRAY (SINDIR) scalar arrays.  It also adds field code namespaces,
    which can be specified with the new /NAMESPACE directive, or else as
    part of an /INCLUDE directive.

  * Some notes about namespaces:

    - Namespaces are separated from field names by a dot (.):
  
          namespace.name
        
      and can be nested arbitrarily deep, separating namespaces with
      intermediate dots:

          namespace.subspace.subsubspace.name

      Namespaces were created to provide an alternative to the prefix and
      suffix added to the /INCLUDE directive in Standards Version 9, which
      have some unfortunate side-effects due to their modifying field names
      directly.  Because namespaces nest and are syntactically separate
      from field names, they do a better job of encapsulation.

    - If the namespace of a field is null (""), which is the default, then
      the dot separating the namespace from the field name may be omitted.

    - An /INCLUDE statement can specify a namespace which becomes the
      included fragment's "root namespace".  The root namespace of the base
      (top-level) format file is always the nullspace (""), and cannot be
      changed.

    - In addition to root namespaces, there is also a "current namespace".
      At the top of a fragment, the current namespace is set to the root
      namespace.  A /NAMESPACE directive can be used to change the current
      namespace to a subspace under the root namespace.  That is, if the
      root namespace is "root", then the directive:

          /NAMESPACE subspace

       changes the current namespace to "root.subspace" regardless of what
       the current namespace was before.  To change the current namespace
       back to the root namespace, use the null token ("") with the
       /NAMESPACE directive:

          /NAMESPACE ""

    - If no namespace is specified in an /INCLUDE line, then the current
      namespace becomes the root namespace of the included fragment.

    - Subnamespaces under the root namespace may also be specified directly
      in the name part of a field specification.  As a result, it is never
      necessary to use the /NAMESPACE directive.

    - Every field code and name in a fragment implicitly gains either the
      fragment's root namespace or the current namespace.  If the field
      code starts with an initial dot, then the root namespace is prepended
      to it, otherwise the current namespace is prepended to it.  Because
      the current namespace is always a subspace of the root namespace,
      this means that metadata in a given fragment is never able to access
      other fields outside its own root namespace.

    - The exception to the above is the implicit INDEX vector, which
      ignores all namespaces attached to it, either implicitly, through the
      current namespace, or explicitly when specified in the metadata.
      This contrasts with the behaviour of the INDEX field in the presence
      of affixes, where it can appears or disappears based on the effects
      of the affixes creating or modifying the specific field name "INDEX".

  * Because syntactically the dot (.) now performs two functions, namely
    both separating namespaces from each other and field names, but also
    separating a field code from a representation suffix, there exists
    ambiguity in the syntax.  To resolve the ambiguity, a new representa-
    tion suffix, .z has been added which does nothing.  As an example, the
    field code:

      name.r

    is interpreted as the real part of the field named "name", assuming
    such a field exists.  To indicate the field named "r" in the namespace
    "name", the field code:

      name.r.z

    must be used.  Note that this ambiguity only exists in a Dirfile where
    both "name" and "name.r" are valid field names.  If the field named
    "name" doesn't exist, then the first field code, "name.r" is unambig-
    uously interpreted as the field "r" in the namespace "name".

  * A note on the SINDIR field: Unlike every other vector field, this
    field produces character string data at the sample rate of it's input
    vector, which may be surprising, in certain instances.

  * GetData has supported FLAC compression since 0.9.0.  Standards Version
    10 now adds "flac" to the list of pre-defined encodings.

  Library Changes:

  * The function gd_array_len() no longer silently ignores a representation
    suffix in the field_code provided.  In most cases, passing a
    representation suffix will now cause this function to fail with a
    GD_E_BAD_CODE error.

  * A couple of unnecessary malloc's have been removed from the field
    code search, reducing the chance of encountering a GD_E_ALLOC error.
    Notably, the functions gd_array_len(), gd_bof(), gd_entry_type(),
    gd_fragment_index(), and gd_spf() will no longer produce this error at
    all.

  * NOTE: The GD_VECTOR_ENTRIES symbol in gd_entry_list() and gd_nentries()
    calls does not match SINDIR entries, only numeric-valued vectors.
    This also affects the corresponding special case functions
    (gd_nvectors(), gd_vector_list() &c.)

  * BUG FIX: When building in ANSI-C mode, the computation of complex-
    valued RECIP fields is now correct.

  * BUG FIX: The gd_include() family of functions now correctly clean up
    after encountering an error.  Previously, encountering a syntax error
    would result in these functions erroneously adding fields specified
    before the syntax error to the DIRFILE, with a bogus fragment index.
    Similarly, when these functions return GD_E_REFERENCE, they no longer
    add the included fragment (excluding the bad /REFERENCE directive) to
    the DIRFILE without telling the caller about it.

  * BUG FIX: gd_alter_protection() wasn't marking affected fragments as
    modified, meaning the change in protection level would be lost upon
    close unless other metadata changes were made to the fragment as well,
    or a flush of the fragment's metadata was triggered explicitly with a
    call to gd_rewrite_fragment().

  * BUG FIX: The metadata update performed by gd_delete() now successfully
    updates all fields which used the deleted field as an input.
    Previously some fields could be skipped, leading to segfaults later
    when these fields were accessed.

  * BUG FIX: gd_add_spec() no longer creates an empty data file while
    failing with GD_E_PROTECT when operating in a fragment with data
    protection turned on.

  * BUG FIX: gd_putdata() now refuses to write to complex-valued LINTERP
    fields.  Previously, the write would succeed as if the imaginary
    part of the field were zero.

  * BUG FIX: gd_nentries() now correctly rejects invalid values for the
    type parameter.

  * BUG FIX GetData now properly deals with circular series of aliases,
    turning them all into dangling aliases.  Previously, the alias
    resolution would terminate at some arbitrary point around the loop,
    resulting in internal errors arising from attempts to use an alias as
    a field.

  * BUG FIX: Several bugs in the I/O positioning performed before reads and
    writes to compressed data have been fixed.  Previously, reads and
    writes could occur in the wrong place in the data stream.  Reported by
    S. J. Benton.

  * BUG FIX: Similarly, a number of bugs associated with random-access
    writes to compressed data files which were causing data corruption have
    been fixed.

  * BUG FIX: When reading LZMA-compressed data, gd_getdata() no longer
    hangs if liblzma returns only part of a multibyte sample.

  * BUG FIX: The FLAC encoding now works correctly with non-native endian
    data.

  * BUG FIX: Writes to ASCII (text) encoded files weren't properly updating
    the file's I/O position, leading to subsequent reads and writes
    occurring in the wrong place.

  * BUG FIX: Trying to open a non-existent, gzip-encoded data file now
    reports the correct error (GD_E_IO; "No such file or directory"),
    instead of segfaulting.  Reported by Matthew Petroff.

  * BUG FIX: A segfault encountered when closing very large compressed
    files after writing to them has been fixed.

  * BUG FIX: Attempting to open a SIE-encoded data file a second time
    after a first attempt failed no longer results in a segfault.

  * BUG FIX: The parser no longer assumes a new string buffer returned by
    the parser callback (by assigning it to pdata->line) has the size given
    by pdata->buflen, which the callback is not required to update, but
    instead determines the buffer size directly.  Previously, this
    assumption could result in a segfault within the parser.

  * BUG FIX: gd_add_polynom() and gd_add_cpolynom() no longer reject valid
    poly_ord values.

  * BUG FIX: The gd_[m]add() family of functions are now better at
    rejecting invalid data types.

  * BUG FIX: A segfault-on-error has been fixed in gd_[m]alter_spec.

  * BUG FIX: The gd_madd() functions longer accept aliases as parent field
    names.

  * BUG FIX: Setting n_fields (for LINCOMs) or poly_ord (for POLYNOMs) to
    an out-of-range value and then calling gd_free_entry_strings() no
    longer results in a segfault.

  * BUG FIX: A rare segfault has been fixed in gd_carrays() and
    gd_strings().

  API Changes:

  * The new function gd_alloc_funcs() allows callers to change the memory
    manager used by GetData to allocate and de-allocate heap buffers that
    it returns.  The functions gd_entry(), gd_error_string(),
    gd_fragment_affixes(), gd_linterp_tablename(), and gd_raw_filename()
    will use this memory manager to allocate the buffers they return.  The
    function gd_free_entry_strings() will use this memory manager to free
    strings.  Even if an alternate memory manager is specified, GetData
    will still use the Standard Library's malloc() and free() for much of
    it's internal storage.

  * A new function, gd_match_entries(), extends the functionality of
    gd_entry_list() and gd_nentries() by additionally allowing both
    searches restricted to a particular fragment and also regular
    expression matching against entry names.

  * A number of functions which used to return -1 on error now instead
    return an appropriate error code, previously only available through
    gd_error().  These error codes are all negative-valued.  Functions
    whose error returns have changed and now do this are:

      gd_add(), gd_add_alias(), all the gd_add_<entry_type>() functions,
      gd_add_spec(), gd_alter_affixes(), all the gd_alter_<entry_type>(),
      functions, gd_alter_encoding(), gd_alter_endianness(),
      gd_alter_entry(), gd_alter_frameoffset(), gd_alter_protection(),
      gd_alter_spec(), gd_array_len(), gd_bof(), gd_delete(), gd_desync(),
      gd_dirfile_standards(), gd_discard(), gd_entry(), gd_entry_type(),
      gd_eof(), gd_flush(), gd_fragment_affixes(), gd_fragment_index(),
      gd_frameoffset(), gd_get_carray(), gd_get_carray_slice(),
      gd_get_constant(), gd_hidden(), gd_hide(), gd_include(),
      gd_include_affix(), gd_include_ns(), gd_madd(), gd_madd_alias(),
      all the gd_madd_<entry_type>() functions, gd_madd_spec(),
      gd_metaflush(), gd_move(), gd_nframes(), gd_open(),
      gd_parent_fragment(), gd_protection(), gd_put_carray(),
      gd_put_carray_slice(), gd_put_const(), gd_raw_close(),
      gd_rename(), gd_rewrite_fragment(), gd_seek(), gd_spf(), gd_sync(),
      gd_tell(), gd_unhide(), gd_uninclude(), gd_validate(),
      gd_verbose_prefix()

  * gd_add_indir(), gd_add_sarray(), gd_add_sindir(), gd_madd_indir(),
    gd_madd_sarray(), gd_madd_sindir(), gd_alter_indir(),
    gd_alter_sarray(), and gd_alter_sindir() have been added to manipulate
    metadata of the new field types.

  * gd_msarrays(), gd_get_sarray(), gd_get_sarray_slice(), gd_put_sarray(),
    gd_put_sarray_slice(), gd_sarrays() have been added to read and write
    SARRAY values.

  * gd_fragment_namespace() and gd_include_ns() have been added to read and
    write the root namespace of a fragment.

  * gd_put_string() now returns zero on success and a negative-valued error
    code on error, as well, following the lead of gd_put_constant() and
    gd_put_sarray().  Also note that the return type is now int, where
    previously it was size_t, despite the documentation having always
    claimed it returned int.

  * A new data type symbol, GD_STRING, exists to represent string data.
    The gd_native_type() function now returns GD_STRING for STRING fields
    (as well as for the new SARRAY and SINDIR fields).

  * The GD_FUNCTION_ALIASES block, and hence the long-deprecated
    GetData-0.6 API, has been removed from getdata.h.  Anyone still using
    the GetData-0.6 API should modernise to avoid known problems with that
    API.

  * The gd_shift_t type, which was used for PHASE field shifts, has been
    deprecated.  It has been replaced with gd_int64_t, which is what it
    was always typedef'd to.

  * BUG FIX: gd_getdata() and gd_putdata() now properly report GD_E_IO when
    an I/O error occurs while reading a LINTERP table.  Previously GD_E_LUT
    would be erroneously returned, as if the table file were empty.

  Bindings Changes:

  * MATLAB: The FLAGS argument to GD_INCLUDE is now optional and defaults
    to zero.

  * C++, F77, F95, PERL: The bindings for gd_put_string() have changed to
    reflect changes in the C library.  Fortran 77 no longer returns a
    n_wrote integer; Fortran 95 implements fgd_put_string a subroutine;
    C++ and Perl bindings now return integer zero on success, and negative
    on error.

  * IDL, MATLAB, PHP BUG FIX: Bindings for the C functions gd_raw_filename
    and gd_linterp_tablename now no longer leak the string returned by the
    C API.

  * PYTHON BUG FIX: A UnicodeEncodeError while assigning to
    dirfile.verbose_prefix no longer results in that attribute being set
    to None.  Instead, it retains its former value, which reflects what
    actually happens in the underlying C library in this case.

  * PYTHON BUG FIX: Objects returned by dirfile.entry() and
    dirfile.fragment() weren't being initialised with the correct reference
    count, leading to memory leaks when they went out of scope.  Reported
    by Alexandra Rahlin.

  Miscellaneous:

  * The --enable-assert configure option, which hasn't done anything for a
    long time, has been removed.

  * A new configure option, --disable-util, can be used to suppress
    building of the executables in the util/ subdirectory.

  * In the standard autotools build system, encodings which use external
    libraries for compression (gzip, bzip2, flac, lzma, slim, zzip, zzslim)
    are now by default built as dynamically loaded modules.  To recover the
    old build behaviour, which put everything into the core GetData library
    binary, pass --disable-modules to ./configure.  Using modules intro-
    duces a runtime dependency on GNU libltdl.  The CMake-based build
    system used in the native Microsoft Windows source release retains the
    old (monolithic) behaviour.

