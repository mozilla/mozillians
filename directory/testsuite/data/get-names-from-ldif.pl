#!/usr/bin/perl -w
#
# get-names-from-ldif.pl
#
# Extract names from LDIF file

for (<>) {
	next if ( ! /^cn:/ );
	chomp;
	s/^cn: //;
	print "$_\n";
}
