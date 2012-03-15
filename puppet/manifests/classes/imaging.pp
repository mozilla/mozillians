class python::imaging {
  include python
  package{'python-imaging':
    ensure => installed,
  }
}
