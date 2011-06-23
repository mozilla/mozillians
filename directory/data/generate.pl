#!/usr/bin/perl -w
#
# generate random names for testing directory systems
#
# usage: generate.pl [-P] [number] [orgDN] [maildomain]
#
# -P adds Posix account data to LDIF file
#
# Creates files:
#	names
#	names.ldif
#	names.passwd

########################################################################
# Operating parameters defaults
########################################################################
my $howmany = 10;
my $PosixLDIF = 0;
my $PeopleDN = "ou=people,dc=mozillians,dc=org";
my $MailDomain = "mozillians.org";
########################################################################
# Output filenames
########################################################################
my $LDIFfile = "names.ldif";
my $NAMESfile = "names";
my $PASSWDfile = "names.passwd";
my $SEARCHfile = "names.search";
########################################################################

if ($ARGV[0] and ($ARGV[0] eq "-P")) {
	shift;
	$PosixLDIF = 1;
}

if (defined($ARGV[0])) {
	$howmany = $ARGV[0];
}
if (defined($ARGV[1])) {
	$PeopleDN = $ARGV[1];
}
if (defined($ARGV[2])) {
	$MailDomain = $ARGV[2];
}


my @given;
open(GIVEN, "given-names") || die("Can't open given-names file");
my $ng = 0;
while (<GIVEN>) {
	chomp;
	$given[$ng++] = $_;
}
close(GIVEN);

my @surnames;
open(SURNAMES, "surnames") || die("Can't open surnames file");
my $ns = 0;
while (<SURNAMES>) {
	chomp;
	$surnames[$ns++] = $_;
}
close(SURNAMES);

# Create output files
open (NAMES, ">$NAMESfile") or die( "Cannot create $NAMESfile\n" );
open (LDIF, ">$LDIFfile") or die( "Cannot create $LDIFfile\n" );
open (SEARCHES, ">$SEARCHfile") or die( "Cannot create $SEARCHfile\n" );
if ($PosixLDIF) {
	open (PASSWD, ">$PASSWDfile") or die( "Cannot create $PASSWDfile\n" );
}

# print "Given: $ng Surname: $ns\n";

for ($count=0;$count<$howmany;$count++) {
	my $s = int (rand $ns);
	my $g = int (rand $ng);
	my $uid = sprintf "u%06d", $count;
	my $gecos = "$given[$g] $surnames[$s]";
	my $uidN = $count+10000;
	my $unique = "7f3a67" . $uid;

	################################################
	# Names file
	################################################
	print NAMES $given[$g], " ", $surnames[$s], "\n";

	################################################
	# Search file
	################################################
	print SEARCHES "ldapsearch -b $PeopleDN  -s sub cn=\"", $given[$g], " ", $surnames[$s], "\"\n";

	################################################
	# LDIF file
	################################################
	printf LDIF "dn: uniqueIdentifier=%s,%s\n", $unique,  $PeopleDN;

	print LDIF "objectclass: inetOrgPerson\nobjectclass: person\n";
	print LDIF "objectclass: mozilliansPerson\n";
	if ($PosixLDIF) {
		print LDIF "objectclass: posixAccount\n";
	}
	print LDIF "displayName: ", $given[$g], " ", $surnames[$s], "\n";
	print LDIF "cn: ", $given[$g], " ", $surnames[$s], "\n";
	print LDIF "sn: ", $surnames[$s], "\n";
	print LDIF "uniqueIdentifier: $unique\n";
	print LDIF "uid: $uid\n";
	# The password is 'secret'
	print LDIF "userPassword: {SSHA}VpIyfHhUQI62WgjTanEzi+NRVHYbu4c+\n";
	print LDIF "mail: $uid\@$MailDomain\n";
	printf LDIF "telephoneNumber: +44 1234 %06d\n", $count+567000;
	if ($PosixLDIF) {
		print LDIF "userPassword: notverysecret\n";
		print LDIF "uidNumber: $uidN\n";
		print LDIF "gidNumber: $uidN\n";
		print LDIF "homeDirectory: /home/$uid\n";
		print LDIF "gecos: $gecos\n";
	}
	# Vouch for some of the test users
	if ($count%3) {
		print LDIF "mozilliansVouchedBy: cn=test,ou=People,dc=mozillians,dc=org\n";
	}
	print LDIF "\n";

	################################################
	# Passwd file
	################################################
	printf PASSWD "%s:%s:%s:%s:%s:%s:%s\n",
		$uid, "UNSETPWXXXXXX",
		$uidN, $uidN,
		$gecos,
		"/home/$uid", "/bin/bash" if ($PosixLDIF);
}
