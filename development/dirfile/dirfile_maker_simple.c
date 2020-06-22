/***************************************************************************
                 dirfile_maker_simple.cpp  -  data source for dirfiles
                             -------------------
    begin                : Tue Oct 21 2003
    copyright            : (C) 2003 C. Barth Netterfield
    email                : netterfield@astro.utoronto.ca
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/


#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <math.h>
#include <sys/time.h>

struct DFEntryType {
  char field[17]; // field name
  int spf; // samples per frame
  int fp; // file pointer
  char type; // data type.  'f' is FLOAT32, 'd' is FLOAT64, 'u' is UINT16. For others see the getdata documentation
};

#define NDF 15
#define SCOUNT 0
#define FCOUNT 1
#define SINE 2
#define SSINE 3
#define COS 4
#define TIME 5
#define EXTRA 6

// a list of fields we are going to create
struct DFEntryType df[NDF] = {
  {"scount", 1, -1, 'f'},
  {"fcount", 20, -1, 'f'},
  {"sine", 20, -1, 'f'},
  {"ssine", 1, -1, 'f'},
  {"cos", 20, -1, 'u'},
  {"time", 20, -1, 'd'},
  {"E0", 20, -1, 'f'},
  {"E1", 20, -1, 'f'},
  {"E2", 20, -1, 'f'},
  {"E3", 20, -1, 'f'},
  {"E4", 20, -1, 'f'},
  {"E5_test", 20, -1, 'f'},
  {"E6_test", 20, -1, 'f'},
  {"E7[m]", 20, -1, 'f'},
  {"E8^2", 20, -1, 'f'}
};
  
int main() {
  char dirfilename[120];
  char tmpstr[150];
  FILE *fpf;
  int i, count = 0;
  int j;
  float x;
  unsigned short sx;
  double dx;
  
  struct timeval tv;
  
  sprintf(dirfilename, "%d.dm", time(NULL));

  printf("Writing dirfile %s\n", dirfilename);
  printf("The fields are:\n");
  for (i=0; i<NDF; i++) {
    printf("%16s %2d samples per frame\n", df[i].field, df[i].spf);
  }
  
  if (mkdir(dirfilename, 00755) < 0) {
    perror("dirfile mkdir()");
    exit(0);
  }
  
  sprintf(tmpstr,"%s/format", dirfilename);

  fpf = fopen(tmpstr,"w");

  /** write the format file, and create/open the raw data files */
  /* entries for the raw fields */
  for (i=0; i<NDF; i++) {
    fprintf(fpf,"%s RAW %c %d\n", df[i].field, df[i].type, df[i].spf);
    fflush(fpf);
    sprintf(tmpstr,"%s/%s", dirfilename, df[i].field);
    df[i].fp = open(tmpstr, O_WRONLY|O_CREAT, 00644); // open the raw data files where the data will be written.
  }

  // create the field COS, which is cos*0.0054931641 -180.
  fprintf(fpf, "COS LINCOM 1 cos 0.0054931641 -180\n");
  
  /* give the field 'cos' units. This can be done for all the fields */
  fprintf(fpf, "COS/units STRING ^o\nCOS/quantity STRING Angle\n");
  
  fclose(fpf);
  /** format file has been writen. */
  /** for more info on the format file, see http://getdata.sourceforge.net/dirfile.html#format
   * in particular, look at the description of the RAW field type to see how this one works
   * and look at the LINCOM field type to see how you can store raw ADC inputs, and create a calibrated version of the data as well
  
  /* make a link to the current dirfile - kst can read this to make life easy... */
  unlink("dm.lnk");
  symlink(dirfilename, "dm.lnk");

  printf("starting loop\n");
  // Every 200 ms, write 1 frame of data to each field.
  // some fields have only 1 sample per frame, but others have 20.
  // see df[].spf, initialized above
  while (1) {
    /* write 'fcount' */
    for (i=0; i<df[FCOUNT].spf; i++) {
      x = count*df[FCOUNT].spf+i;
      write(df[FCOUNT].fp, &x, sizeof(float));
    }

    /* write 'sine' */
    for (i=0; i<df[SINE].spf; i++) {
      dx = count*df[SINE].spf+i;
      x = sin(2.0*M_PI*dx/100.0);
      write(df[SINE].fp, &x, sizeof(float));
    }
    
    /* write 'ssine' */
    for (i=0; i<df[SSINE].spf; i++) {
      dx = count*df[SSINE].spf+i;
      x = sin(2.0*M_PI*dx/100.0);
      write(df[SSINE].fp, &x, sizeof(float));
    }
    
    /* write 'cos' */
    for (i=0; i<df[COS].spf; i++) {
      dx = count*df[COS].spf+i;
      sx = 4000*cos(2.0*M_PI*dx/100.0) + 32768;
      write(df[COS].fp, &sx, sizeof(unsigned short));
    }
  
    gettimeofday(&tv, 0);
    for (i=0; i<df[TIME].spf; i++) {
      dx = (double)tv.tv_sec +( double)(tv.tv_usec)/1000000.0 + (double)i/100.0;
      write(df[TIME].fp, &dx, sizeof(double));
    }
    
    /* write extras */
    for (j=6; j<NDF; j++) {
      for (i=0; i<df[j].spf; i++) {
        x = (double)rand()/(double)RAND_MAX;
        write(df[j].fp, &x, sizeof(float));
      }
    }

    /* write 'count' */
    x = count;
    write(df[SCOUNT].fp, &x, sizeof(float));


    printf("writing frame %d  \r", count);
    fflush(stdout);
    usleep(200000);
    count++;
  }
  return (0);
}