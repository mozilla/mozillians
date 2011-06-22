#!/usr/bin/perl
#
# MyConfig - read simple config that is used by OpenLDAP setup
#
# $Id: MyConfig.pm 44 2006-01-31 19:38:02Z afindlay $

use strict;

package MyConfig;

sub readConfig {
	my ($filename) = @_;

	open CONF, "<$filename" or die "Cannot open $filename";

	my $ret = {};
	while (<CONF>) {
		chomp;
		next if /^\s*#/;
		next if /^\s*$/;

		my ($name,$value) = ($_ =~ /([a-zA-Z_-]+)=(.+)$/);
		$ret->{$name} = $value;
	}
	close CONF;

	return $ret;
}

1;

