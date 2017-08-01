%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%define pulp_admin 0
%define pulp_server 1

# define required pulp platform version.
%define pulp_version 2.10.1

%define inst_prefix pulp_snapshot

# ---- Pulp (snapshot) ------------------------------------------------------------

Name: pulp-snapshot
Version: 0.3
Release: 1%{?dist}
Summary: Distributor that snapshots the state of a repository at publish time
Group: Development/Languages
License: Apache
URL: https://gitlab.sas.com
Source0: %{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%description
Provides a distributor for snapshotting pulp repositories

%prep
%setup -q

%build

pushd common
%{__python} setup.py build
popd

%if %{pulp_admin}
pushd extensions_admin
%{__python} setup.py build
popd
%endif # End pulp_admin if block

%if %{pulp_server}
pushd plugins
%{__python} setup.py build
popd
%endif # End pulp_server if block

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/%{_sysconfdir}/pulp

pushd common
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

%if %{pulp_admin}
pushd extensions_admin
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
%endif # End pulp_admin if block

%if %{pulp_server}
pushd plugins
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins
%endif # End pulp_server if block

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

%clean
rm -rf %{buildroot}


# ---- Common --------------------------------------------------------------

%package -n python-%{name}-common
Summary: Pulp SAS Metadata support common library
Group: Development/Languages

%description -n python-%{name}-common
A collection of modules shared among all SAS Metadata components.

%files -n python-%{name}-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/%{inst_prefix}
%{python_sitelib}/%{inst_prefix}_common*.egg-info
%{python_sitelib}/%{inst_prefix}/__init__.py*
%{python_sitelib}/%{inst_prefix}/common/
%doc LICENSE

# ---- Plugins -----------------------------------------------------------------
%if %{pulp_server}
%package plugins
Summary: Pulp Win plugins
Group: Development/Languages
Requires: python-%{name}-common = %{version}-%{release}
Requires: pulp-server
# rpm-python needed for version comparison
Requires: rpm-python

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Win specific support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/%{inst_prefix}/plugins/
%{python_sitelib}/%{inst_prefix}_plugins*.egg-info
%{_usr}/lib/pulp/plugins/types/snapshot.json
%defattr(-,apache,apache,-)
%defattr(-,root,root,-)
%doc LICENSE
%endif # End pulp_server if block


# ---- Admin Extensions --------------------------------------------------------
%if %{pulp_admin}
%package admin-extensions
Summary: The Win admin client extensions
Group: Development/Languages
Requires: pulp-admin-client
Requires: python-%{name}-common = %{version}-%{release}
# Needed for version_utils
Requires: python-pulp-rpm-common

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with Win specific features.

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/%{inst_prefix}_extensions_admin*.egg-info
%{python_sitelib}/%{inst_prefix}/extensions/__init__.py*
%{python_sitelib}/%{inst_prefix}/extensions/admin/
%doc LICENSE
%endif # End pulp_admin if block

%changelog
* Wed Jan  6 2016 Mihai Ibanescu <mihai.ibanescu@sas.com> - 0.1-1
- Initial spec
