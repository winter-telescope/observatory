int
add_bit(dirfile, field_code, in_field, bitnum, numbits, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	int bitnum
	int numbits
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_bit = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i, %i, %i", dirfile, field_code, in_field, bitnum, numbits, fragment_index);
		RETVAL = gd_add_bit(dirfile, field_code, in_field, bitnum, numbits, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_lincom(dirfile, field_code, n_fields, in_fields, cm, cb, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	int n_fields
	const char ** in_fields
	gdp_complex_in cm
	gdp_complex_in cb
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_lincom = 1
	CODE:
		dtrace("%p, \"%s\", %i, %p, %p, %p, %i", dirfile, field_code, n_fields, in_fields, cm, cb, fragment_index);
		RETVAL = gd_add_clincom(dirfile, field_code, n_fields, in_fields, cm, cb, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		safefree(in_fields);
		safefree(cm);
		safefree(cb);
		dreturn("%i", RETVAL);

int
add_polynom(dirfile, field_code, poly_ord, in_field, ca, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	int poly_ord
	const char * in_field
	gdp_complex_in ca
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_polynom = 1
	CODE:
		dtrace("%p, \"%s\", %i, \"%s\", %p, %i", dirfile, field_code, poly_ord, in_field, ca, fragment_index);
		RETVAL = gd_add_cpolynom(dirfile, field_code, poly_ord, in_field, ca, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		safefree(ca);
		dreturn("%i", RETVAL);

int
add_recip(dirfile, field_code, in_field, cdividend, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	gdp_complex cdividend
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_recip = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %g;%g, %i", dirfile, field_code, in_field, creal(cdividend), cimag(cdividend), fragment_index);
		RETVAL = gd_add_crecip(dirfile, field_code, in_field, cdividend, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_divide(dirfile, field_code, in_field1, in_field2, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field1
	const char * in_field2
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_divide = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i", dirfile, field_code, in_field1, in_field2, fragment_index);
		RETVAL = gd_add_divide(dirfile, field_code, in_field1, in_field2, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_linterp(dirfile, field_code, in_field, table, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	const char * table
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_linterp = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i", dirfile, field_code, in_field, table, fragment_index);
		RETVAL = gd_add_linterp(dirfile, field_code, in_field, table, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_multiply(dirfile, field_code, in_field1, in_field2, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field1
	const char * in_field2
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_multiply = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i", dirfile, field_code, in_field1, in_field2, fragment_index);
		RETVAL = gd_add_multiply(dirfile, field_code, in_field1, in_field2, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_phase(dirfile, field_code, in_field, shift, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	gd_int64_t shift
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_phase = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %" PRId64 ", %i", dirfile, field_code, in_field, shift, fragment_index);
		RETVAL = gd_add_phase(dirfile, field_code, in_field, shift, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_sbit(dirfile, field_code, in_field, bitnum, numbits, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	int bitnum
	int numbits
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_sbit = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i, %i, %i", dirfile, field_code, in_field, bitnum, numbits, fragment_index);
		RETVAL = gd_add_sbit(dirfile, field_code, in_field, bitnum, numbits, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_string(dirfile, field_code, value, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * value
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_string = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i", dirfile, field_code, value, fragment_index);
		RETVAL = gd_add_string(dirfile, field_code, value, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_bit(dirfile, field_code, in_field=NULL, bitnum=-1, numbits=0)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_ffff_t bitnum
	gdp_numbits_t numbits
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_bit = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i, %i", dirfile, field_code, in_field, bitnum, numbits);
		RETVAL = gd_alter_bit(dirfile, field_code, in_field, bitnum, numbits);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_carray(dirfile, field_code, const_type, array_len)
	DIRFILE* dirfile
	const char* field_code
	gd_type_t const_type
	size_t array_len
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_carray = 1
	CODE:
		dtrace("%p, %p, 0x%03X, %" PRIuSIZE "", dirfile, field_code, const_type, array_len);
		RETVAL = gd_alter_carray(dirfile, field_code, const_type, array_len);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_lincom(dirfile, field_code, n_fields=0, in_fields=NULL, m=NULL, b=NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_int n_fields
	const char ** in_fields
	gdp_complex_undef m
	gdp_complex_undef b
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_lincom = 1
	CODE:
		dtrace("%p, \"%s\", %i, %p, %p, %p", dirfile, field_code, n_fields, in_fields, m, b);
		RETVAL = gd_alter_clincom(dirfile, field_code, n_fields, in_fields, m, b);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		safefree(in_fields);
		safefree(m);
		safefree(b);
		dreturn("%i", RETVAL);

int
alter_polynom(dirfile, field_code, poly_ord=0, in_field=NULL, a=NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_int poly_ord
	gdp_char * in_field
	gdp_complex_undef a
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_polynom = 1
	CODE:
		dtrace("%p, \"%s\", %i, \"%s\", %p", dirfile, field_code, poly_ord, in_field, a);
		RETVAL = gd_alter_cpolynom(dirfile, field_code, poly_ord, in_field, a);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		safefree(a);
		dreturn("%i", RETVAL);

int
alter_recip(dirfile, field_code, in_field=NULL, cdividend)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_complex cdividend
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_recip = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %g;%g", dirfile, field_code, in_field, creal(cdividend), cimag(cdividend));
		RETVAL = gd_alter_crecip(dirfile, field_code, in_field, cdividend);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_divide(dirfile, field_code, in_field1=NULL, in_field2=NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field1
	gdp_char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_divide = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\"", dirfile, field_code, in_field1, in_field2);
		RETVAL = gd_alter_divide(dirfile, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_multiply(dirfile, field_code, in_field1=NULL, in_field2=NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field1
	gdp_char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_multiply = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\"", dirfile, field_code, in_field1, in_field2);
		RETVAL = gd_alter_multiply(dirfile, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_phase(dirfile, field_code, in_field, shift)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_int64_t shift
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_phase = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %" PRId64 "", dirfile, field_code, in_field, shift);
		RETVAL = gd_alter_phase(dirfile, field_code, in_field, shift);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_sbit(dirfile, field_code, in_field=NULL, bitnum=-1, numbits=0)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_ffff_t bitnum
	gdp_numbits_t numbits
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_sbit = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i, %i", dirfile, field_code, in_field, bitnum, numbits);
		RETVAL = gd_alter_sbit(dirfile, field_code, in_field, bitnum, numbits);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

size_t
array_len(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::array_len = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_array_len(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRIuSIZE "", RETVAL);

unsigned long int
encoding(dirfile, fragment)
	DIRFILE * dirfile
	int fragment
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::encoding = 1
	CODE:
		dtrace("%p, %i", dirfile, fragment);
		RETVAL = gd_encoding(dirfile, fragment);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%lu", RETVAL);

unsigned long int
endianness(dirfile, fragment)
	DIRFILE * dirfile
	int fragment
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::endianness = 1
	CODE:
		dtrace("%p, %i", dirfile, fragment);
		RETVAL = gd_endianness(dirfile, fragment);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%lu", RETVAL);

int
fragment_index(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::fragment_index = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_fragment_index(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

const char *
fragmentname(dirfile, index)
	DIRFILE * dirfile
	int index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::fragmentname = 1
	CODE:
		dtrace("%p, %i", dirfile, index);
		RETVAL = gd_fragmentname(dirfile, index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);

int
madd(dirfile, entry, parent)
	DIRFILE * dirfile
	gd_entry_t & entry
	const char * parent
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd = 1
	CODE:
		dtrace("%p, %p, \"%s\"", dirfile, &entry, parent);
		RETVAL = gd_madd(dirfile, &entry, parent);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_bit(dirfile, parent, field_code, in_field, bitnum, numbits)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	int bitnum
	int numbits
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_bit = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i, %i", dirfile, parent, field_code, in_field, bitnum, numbits);
		RETVAL = gd_madd_bit(dirfile, parent, field_code, in_field, bitnum, numbits);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_lincom(dirfile, parent, field_code, n_fields, in_fields, cm, cb)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	int n_fields
	const char ** in_fields
	gdp_complex_in cm
	gdp_complex_in cb
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_lincom = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i, %p, %p, %p", dirfile, parent, field_code, n_fields, in_fields, cm, cb);
		RETVAL = gd_madd_clincom(dirfile, parent, field_code, n_fields, in_fields, cm, cb);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		safefree(in_fields);
		safefree(cm);
		safefree(cb);
		dreturn("%i", RETVAL);

int
madd_polynom(dirfile, parent, field_code, poly_ord, in_field, ca)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	int poly_ord
	const char * in_field
	gdp_complex_in ca
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_polynom = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i, \"%s\", %p", dirfile, parent, field_code, poly_ord, in_field, ca);
		RETVAL = gd_madd_cpolynom(dirfile, parent, field_code, poly_ord, in_field, ca);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		safefree(ca);
		dreturn("%i", RETVAL);

int
madd_recip(dirfile, parent, field_code, in_field, cdividend)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	gdp_complex cdividend
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_recip = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %g;%g", dirfile, parent, field_code, in_field, creal(cdividend), cimag(cdividend));
		RETVAL = gd_madd_crecip(dirfile, parent, field_code, in_field, cdividend);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_divide(dirfile, parent, field_code, in_field1, in_field2)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field1
	const char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_divide = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, in_field1, in_field2);
		RETVAL = gd_madd_divide(dirfile, parent, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_linterp(dirfile, parent, field_code, in_field, table)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	const char * table
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_linterp = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, in_field, table);
		RETVAL = gd_madd_linterp(dirfile, parent, field_code, in_field, table);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_multiply(dirfile, parent, field_code, in_field1, in_field2)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field1
	const char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_multiply = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, in_field1, in_field2);
		RETVAL = gd_madd_multiply(dirfile, parent, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_phase(dirfile, parent, field_code, in_field, shift)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	gd_int64_t shift
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_phase = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %" PRId64 "", dirfile, parent, field_code, in_field, shift);
		RETVAL = gd_madd_phase(dirfile, parent, field_code, in_field, shift);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_sbit(dirfile, parent, field_code, in_field, bitnum, numbits)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	int bitnum
	int numbits
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_sbit = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i, %i", dirfile, parent, field_code, in_field, bitnum, numbits);
		RETVAL = gd_madd_sbit(dirfile, parent, field_code, in_field, bitnum, numbits);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_spec(dirfile, line, parent)
	DIRFILE * dirfile
	const char * line
	const char * parent
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_spec = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\"", dirfile, line, parent);
		RETVAL = gd_madd_spec(dirfile, line, parent);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_string(dirfile, parent, field_code, value)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * value
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_string = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, value);
		RETVAL = gd_madd_string(dirfile, parent, field_code, value);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
dirfile_standards(dirfile, version=GD_VERSION_CURRENT)
	DIRFILE * dirfile
	int version
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::dirfile_standards = 1
	CODE:
		dtrace("%p, %i", dirfile, version);
		RETVAL = gd_dirfile_standards(dirfile, version);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

const char *
dirfilename(dirfile)
	DIRFILE * dirfile
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::dirfilename = 1
	CODE:
		dtrace("%p", dirfile);
		RETVAL = gd_dirfilename(dirfile);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);

gd_type_t
native_type(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::native_type = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_native_type(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("0x%03X", RETVAL);

int
parent_fragment(dirfile, fragment_index)
	DIRFILE * dirfile
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::parent_fragment = 1
	CODE:
		dtrace("%p, %i", dirfile, fragment_index);
		RETVAL = gd_parent_fragment(dirfile, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_protection(dirfile, protection_level, fragment_index)
	DIRFILE * dirfile
	int protection_level
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_protection = 1
	CODE:
		dtrace("%p, %i, %i", dirfile, protection_level, fragment_index);
		RETVAL = gd_alter_protection(dirfile, protection_level, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
protection(dirfile, fragment_index)
	DIRFILE * dirfile
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::protection = 1
	CODE:
		dtrace("%p, %i", dirfile, fragment_index);
		RETVAL = gd_protection(dirfile, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

const char *
raw_filename(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::raw_filename = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_raw_filename(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);

const char *
reference(dirfile, field_code=NULL)
	DIRFILE * dirfile
	gdp_char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::reference = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_reference(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);

unsigned int
spf(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::spf = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_spf(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%u", RETVAL);

int
put_string(dirfile, field_code, data)
	DIRFILE * dirfile
	const char * field_code
	const char * data
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::put_string = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\"", dirfile, field_code, data);
		RETVAL = gd_put_string(dirfile, field_code, data);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
validate(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::validate = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_validate(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add(dirfile, entry)
	DIRFILE * dirfile
	gd_entry_t & entry
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add = 1
	CODE:
		dtrace("%p, %p", dirfile, &entry);
		RETVAL = gd_add(dirfile, &entry);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_raw(dirfile, field_code, data_type, spf, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	gd_type_t data_type
	unsigned int spf
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_raw = 1
	CODE:
		dtrace("%p, \"%s\", 0x%03X, %u, %i", dirfile, field_code, data_type, spf, fragment_index);
		RETVAL = gd_add_raw(dirfile, field_code, data_type, spf, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_spec(dirfile, line, fragment_index=0)
	DIRFILE * dirfile
	const char * line
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_spec = 1
	CODE:
		dtrace("%p, \"%s\", %i", dirfile, line, fragment_index);
		RETVAL = gd_add_spec(dirfile, line, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_const(dirfile, field_code, const_type=GD_NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_type_t const_type
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_const = 1
	CODE:
		dtrace("%p, \"%s\", 0x%03X", dirfile, field_code, const_type);
		RETVAL = gd_alter_const(dirfile, field_code, const_type);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_encoding(dirfile, encoding, fragment=0, recode=0)
	DIRFILE * dirfile
	unsigned long int encoding
	int fragment
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_encoding = 1
	CODE:
		dtrace("%p, %lu, %i, %i", dirfile, encoding, fragment, recode);
		RETVAL = gd_alter_encoding(dirfile, encoding, fragment, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_endianness(dirfile, byte_sex, fragment=0, recode=0)
	DIRFILE * dirfile
	unsigned long int byte_sex
	int fragment
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_endianness = 1
	CODE:
		dtrace("%p, %lu, %i, %i", dirfile, byte_sex, fragment, recode);
		RETVAL = gd_alter_endianness(dirfile, byte_sex, fragment, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_entry(dirfile, field_code, entry, recode=0)
	DIRFILE * dirfile
	const char * field_code
	gdp_pentry_t & entry
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_entry = 1
	CODE:
		dtrace("%p, \"%s\", %p, %i", dirfile, field_code, &entry, recode);
		RETVAL = gd_alter_entry(dirfile, field_code, &entry, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_linterp(dirfile, field_code, in_field=NULL, table=NULL, recode=0)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_char * table
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_linterp = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i", dirfile, field_code, in_field, table, recode);
		RETVAL = gd_alter_linterp(dirfile, field_code, in_field, table, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_raw(dirfile, field_code, data_type=GD_NULL, spf=0, recode=0)
	DIRFILE * dirfile
	const char * field_code
	gdp_type_t data_type
	gdp_uint_t spf
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_raw = 1
	CODE:
		dtrace("%p, \"%s\", 0x%03X, %u, %i", dirfile, field_code, data_type, spf, recode);
		RETVAL = gd_alter_raw(dirfile, field_code, data_type, spf, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_spec(dirfile, line, recode=0)
	DIRFILE * dirfile
	const char * line
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_spec = 1
	CODE:
		dtrace("%p, \"%s\", %i", dirfile, line, recode);
		RETVAL = gd_alter_spec(dirfile, line, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
delete(dirfile, field_code, flags=0)
	DIRFILE * dirfile
	const char * field_code
	int flags
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::delete = 1
	CODE:
		dtrace("%p, \"%s\", %i", dirfile, field_code, flags);
		RETVAL = gd_delete(dirfile, field_code, flags);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
flush(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::flush = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_flush(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
malter_spec(dirfile, line, parent, recode=0)
	DIRFILE * dirfile
	const char * line
	const char * parent
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::malter_spec = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i", dirfile, line, parent, recode);
		RETVAL = gd_malter_spec(dirfile, line, parent, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
metaflush(dirfile)
	DIRFILE * dirfile
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::metaflush = 1
	CODE:
		dtrace("%p", dirfile);
		RETVAL = gd_metaflush(dirfile);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
move(dirfile, field_code, new_fragment, flags=0)
	DIRFILE * dirfile
	const char * field_code
	int new_fragment
	unsigned int flags
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::move = 1
	CODE:
		dtrace("%p, \"%s\", %i, %u", dirfile, field_code, new_fragment, flags);
		RETVAL = gd_move(dirfile, field_code, new_fragment, flags);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
rename(dirfile, old_code, new_name, move_data=0)
	DIRFILE * dirfile
	const char * old_code
	const char * new_name
	int move_data
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::rename = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i", dirfile, old_code, new_name, move_data);
		RETVAL = gd_rename(dirfile, old_code, new_name, move_data);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
rewrite_fragment(dirfile, fragment)
	DIRFILE * dirfile
	int fragment
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::rewrite_fragment = 1
	CODE:
		dtrace("%p, %i", dirfile, fragment);
		RETVAL = gd_rewrite_fragment(dirfile, fragment);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
uninclude(dirfile, fragment_index, del=0)
	DIRFILE * dirfile
	int fragment_index
	int del
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::uninclude = 1
	CODE:
		dtrace("%p, %i, %i", dirfile, fragment_index, del);
		RETVAL = gd_uninclude(dirfile, fragment_index, del);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_frameoffset(dirfile, offset, fragment=0, recode=0)
	DIRFILE * dirfile
	gd_off64_t offset
	int fragment
	int recode
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_frameoffset = 1
	CODE:
		dtrace("%p, %" PRId64 ", %i, %i", dirfile, (int64_t)offset, fragment, recode);
		RETVAL = gd_alter_frameoffset64(dirfile, offset, fragment, recode);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

gd_off64_t
frameoffset(dirfile, fragment)
	DIRFILE * dirfile
	int fragment
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::frameoffset = 1
	CODE:
		dtrace("%p, %i", dirfile, fragment);
		RETVAL = gd_frameoffset64(dirfile, fragment);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRId64 "", (int64_t)RETVAL);

double
framenum(dirfile, field_code_in, value, field_start=0, field_end=0)
	DIRFILE * dirfile
	const char* field_code_in
	double value
	gd_off64_t field_start
	gd_off64_t field_end
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::framenum = 1
	CODE:
		dtrace("%p, %p, %g, %" PRId64 ", %" PRId64 "", dirfile, field_code_in, value, (int64_t)field_start, (int64_t)field_end);
		RETVAL = gd_framenum_subset64(dirfile, field_code_in, value, field_start, field_end);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%g", RETVAL);

gd_off64_t
nframes(dirfile)
	DIRFILE * dirfile
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::nframes = 1
	CODE:
		dtrace("%p", dirfile);
		RETVAL = gd_nframes64(dirfile);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRId64 "", (int64_t)RETVAL);

gd_off64_t
bof(dirfile, field_code)
	DIRFILE * dirfile
	const char* field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::bof = 1
	CODE:
		dtrace("%p, %p", dirfile, field_code);
		RETVAL = gd_bof64(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRId64 "", (int64_t)RETVAL);

gd_off64_t
eof(dirfile, field_code)
	DIRFILE * dirfile
	const char* field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::eof = 1
	CODE:
		dtrace("%p, %p", dirfile, field_code);
		RETVAL = gd_eof64(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRId64 "", (int64_t)RETVAL);

int
error_count(dirfile)
	DIRFILE * dirfile
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::error_count = 1
	CODE:
		dtrace("%p", dirfile);
		RETVAL = gd_error_count(dirfile);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

gd_off64_t
seek(dirfile, field_code, frame_num, sample_num, flags=GD_SEEK_SET)
	DIRFILE * dirfile
	const char* field_code
	gd_off64_t frame_num
	gd_off64_t sample_num
	int flags
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::seek = 1
	CODE:
		dtrace("%p, %p, %" PRId64 ", %" PRId64 ", %i", dirfile, field_code, (int64_t)frame_num, (int64_t)sample_num, flags);
		RETVAL = gd_seek(dirfile, field_code, frame_num, sample_num, flags);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRId64 "", (int64_t)RETVAL);

gd_off64_t
tell(dirfile, field_code)
	DIRFILE * dirfile
	const char* field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::tell = 1
	CODE:
		dtrace("%p, %p", dirfile, field_code);
		RETVAL = gd_tell(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%" PRId64 "", (int64_t)RETVAL);

int
hide(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::hide = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_hide(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
hidden(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::hidden = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_hidden(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
unhide(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::unhide = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_unhide(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
sync(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::sync = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_sync(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

const char *
alias_target(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alias_target = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_alias_target(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);

int
add_alias(dirfile, field_code, target, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * target
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_alias = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", %i", dirfile, field_code, target, fragment_index);
		RETVAL = gd_add_alias(dirfile, field_code, target, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_alias(dirfile, parent, field_code, target)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * target
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_alias = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, target);
		RETVAL = gd_madd_alias(dirfile, parent, field_code, target);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_window(dirfile, field_code, in_field, check_field, windop, threshold, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	const char * check_field
	gd_windop_t windop
	gd_triplet_t threshold
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_window = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i, {%g,%" PRIX64 ",%" PRId64 "}, %i", dirfile, field_code, in_field, check_field, windop, threshold.r, threshold.u, threshold.i, fragment_index);
		RETVAL = gd_add_window(dirfile, field_code, in_field, check_field, windop, threshold, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_window(dirfile, parent, field_code, in_field, check_field, windop, threshold)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	const char * check_field
	gd_windop_t windop
	gd_triplet_t threshold
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_window = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\", %i, {%g,%" PRIX64 ",%" PRId64 "}", dirfile, parent, field_code, in_field, check_field, windop, threshold.r, threshold.u, threshold.i);
		RETVAL = gd_madd_window(dirfile, parent, field_code, in_field, check_field, windop, threshold);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_window(dirfile, field_code, in_field, check_field, windop, threshold)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_char * check_field
	gd_windop_t windop
	gd_triplet_t threshold
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_window = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i, {%g,%" PRIX64 ",%" PRId64 "}", dirfile, field_code, in_field, check_field, windop, threshold.r, threshold.u, threshold.i);
		RETVAL = gd_alter_window(dirfile, field_code, in_field, check_field, windop, threshold);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_affixes(dirfile, index, prefix, suffix=NULL)
	DIRFILE * dirfile
	int index
	gdp_char * prefix
	gdp_char * suffix
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_affixes = 1
	CODE:
		dtrace("%p, %i, \"%s\", \"%s\"", dirfile, index, prefix, suffix);
		RETVAL = gd_alter_affixes(dirfile, index, prefix, suffix);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_mplex(dirfile, field_code, in_field, count_field, count_val, period, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field
	const char * count_field
	int count_val
	int period
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_mplex = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i, %i, %i", dirfile, field_code, in_field, count_field, count_val, period, fragment_index);
		RETVAL = gd_add_mplex(dirfile, field_code, in_field, count_field, count_val, period, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_mplex(dirfile, field_code, in_field=NULL, count_field=NULL, count_val=-1, period=-1)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field
	gdp_char * count_field
	int count_val
	int period
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_mplex = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i, %i", dirfile, field_code, in_field, count_field, count_val, period);
		RETVAL = gd_alter_mplex(dirfile, field_code, in_field, count_field, count_val, period);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_mplex(dirfile, parent, field_code, in_field, count_field, count_val, period)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field
	const char * count_field
	int count_val
	int period
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_mplex = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\", %i, %i", dirfile, parent, field_code, in_field, count_field, count_val, period);
		RETVAL = gd_madd_mplex(dirfile, parent, field_code, in_field, count_field, count_val, period);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
raw_close(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::raw_close = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_raw_close(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
desync(dirfile, flags=0)
	DIRFILE * dirfile
	unsigned int flags
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::desync = 1
	CODE:
		dtrace("%p, %u", dirfile, flags);
		RETVAL = gd_desync(dirfile, flags);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

unsigned long int
flags(dirfile, set=0, reset=0)
	DIRFILE * dirfile
	unsigned long int set
	unsigned long int reset
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::flags = 1
	CODE:
		dtrace("%p, %lu, %lu", dirfile, set, reset);
		RETVAL = gd_flags(dirfile, set, reset);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%lu", RETVAL);

int
verbose_prefix(dirfile, prefix=NULL)
	DIRFILE * dirfile
	gdp_char * prefix
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::verbose_prefix = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, prefix);
		RETVAL = gd_verbose_prefix(dirfile, prefix);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

void
mplex_lookback(dirfile, lookback)
	DIRFILE * dirfile
	int lookback
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::mplex_lookback = 1
	CODE:
		dtrace("%p, %i", dirfile, lookback);
		gd_mplex_lookback(dirfile, lookback);
	CLEANUP:
		dreturnvoid();

char *
linterp_tablename(dirfile, field_code)
	DIRFILE * dirfile
	const char * field_code
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::linterp_tablename = 1
	CODE:
		dtrace("%p, \"%s\"", dirfile, field_code);
		RETVAL = gd_linterp_tablename(dirfile, field_code);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);
		safefree(RETVAL);

int
alter_sarray(dirfile, field_code, array_len)
	DIRFILE* dirfile
	const char* field_code
	size_t array_len
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_sarray = 1
	CODE:
		dtrace("%p, %p, %" PRIuSIZE "", dirfile, field_code, array_len);
		RETVAL = gd_alter_sarray(dirfile, field_code, array_len);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_indir(dirfile, field_code, in_field1, in_field2, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field1
	const char * in_field2
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_indir = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i", dirfile, field_code, in_field1, in_field2, fragment_index);
		RETVAL = gd_add_indir(dirfile, field_code, in_field1, in_field2, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
add_sindir(dirfile, field_code, in_field1, in_field2, fragment_index=0)
	DIRFILE * dirfile
	const char * field_code
	const char * in_field1
	const char * in_field2
	int fragment_index
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::add_sindir = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", %i", dirfile, field_code, in_field1, in_field2, fragment_index);
		RETVAL = gd_add_sindir(dirfile, field_code, in_field1, in_field2, fragment_index);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_indir(dirfile, field_code, in_field1=NULL, in_field2=NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field1
	gdp_char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_indir = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\"", dirfile, field_code, in_field1, in_field2);
		RETVAL = gd_alter_indir(dirfile, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
alter_sindir(dirfile, field_code, in_field1=NULL, in_field2=NULL)
	DIRFILE * dirfile
	const char * field_code
	gdp_char * in_field1
	gdp_char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::alter_sindir = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\"", dirfile, field_code, in_field1, in_field2);
		RETVAL = gd_alter_sindir(dirfile, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_indir(dirfile, parent, field_code, in_field1, in_field2)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field1
	const char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_indir = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, in_field1, in_field2);
		RETVAL = gd_madd_indir(dirfile, parent, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
madd_sindir(dirfile, parent, field_code, in_field1, in_field2)
	DIRFILE * dirfile
	const char * parent
	const char * field_code
	const char * in_field1
	const char * in_field2
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::madd_sindir = 1
	CODE:
		dtrace("%p, \"%s\", \"%s\", \"%s\", \"%s\"", dirfile, parent, field_code, in_field1, in_field2);
		RETVAL = gd_madd_sindir(dirfile, parent, field_code, in_field1, in_field2);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

int
include_affix(dirfile, file, fragment_index, prefix=NULL, suffix=NULL, flags=0)
	DIRFILE * dirfile
	const char * file
	int fragment_index
	gdp_char * prefix
	gdp_char * suffix
	unsigned long int flags
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::include_affix = 1
	CODE:
		dtrace("%p, \"%s\", %i, \"%s\", \"%s\", %lu", dirfile, file, fragment_index, prefix, suffix, flags);
		RETVAL = gd_include_affix(dirfile, file, fragment_index, prefix, suffix, flags);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("%i", RETVAL);

const char *
fragment_namespace(dirfile, fragment, namespace=NULL)
	DIRFILE * dirfile
	int fragment
	gdp_char * namespace
	PREINIT:
		GDP_DIRFILE_ALIAS;
	ALIAS:
		GetData::Dirfile::fragment_namespace = 1
	CODE:
		dtrace("%p, %i, \"%s\"", dirfile, fragment, namespace);
		RETVAL = gd_fragment_namespace(dirfile, fragment, namespace);
		GDP_UNDEF_ON_ERROR();
	OUTPUT:
		RETVAL
	CLEANUP:
		dreturn("\"%s\"", RETVAL);

