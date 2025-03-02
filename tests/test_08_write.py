import csv
import os
import pytest
from datetime import datetime
from shapely.geometry import Point, LineString
from copy import deepcopy
import pandas as pd
import geopandas as gp
import lxml

from .fixtures import population_heh
from pam.activity import Activity, Leg
from pam.core import Household, Person, Population
from pam import write
from pam.write import write_matsim, write_matsim_v12,  \
    write_v11_matsim_plans, write_matsim_v11_attributes, write_od_matrices
from pam.read import read_matsim
from pam.utils import minutes_to_datetime as mtdt
from pam.variables import END_OF_DAY


def test_write_plans_xml(tmp_path, population_heh):
    location = str(tmp_path / "test.xml")
    write_v11_matsim_plans(population_heh, path=location, comment="test")
    expected_file = "{}/test.xml".format(tmp_path)
    assert os.path.exists(expected_file)
    xml_obj = lxml.etree.parse(expected_file)
    dtd = write.v11_plans_dtd()
    assert dtd.validate(xml_obj), dtd.error_log.filter_from_errors()


def test_write_plans_gzip(tmp_path, population_heh):
    location = str(tmp_path / "test.xml.gz")
    write_v11_matsim_plans(population_heh, path=location, comment="test")
    expected_file = "{}/test.xml.gz".format(tmp_path)
    assert os.path.exists(expected_file)


def test_write_attributes_xml(tmp_path, population_heh):
    location = str(tmp_path / "test.xml")
    write_matsim_v11_attributes(population_heh, location=location, comment="test")
    expected_file = "{}/test.xml".format(tmp_path)
    assert os.path.exists(expected_file)
    xml_obj = lxml.etree.parse(expected_file)
    dtd = write.object_attributes_dtd()
    assert dtd.validate(xml_obj), dtd.error_log.filter_from_errors()


def test_write_attributes_gzip(tmp_path, population_heh):
    location = str(tmp_path / "test.xml.gz")
    write_matsim_v11_attributes(population_heh, location=location, comment="test")

    expected_file = "{}/test.xml.gz".format(tmp_path)
    assert os.path.exists(expected_file)


def test_write_plans_xml_assert_contents(tmp_path):
    population = Population()
    hh = Household('a')
    p = Person('a', attributes={'1':'1'})
    p.add(Activity(
        act="home",
        loc=Point((0,0)),
        start_time=datetime(1900,1,1,0,0,0),
        end_time=datetime(1900,1,1,8,0,0)
        ))
    p.add(Leg(
        mode='car',
        start_loc=Point((0,0)),
        end_loc=Point((0,1000)),
        start_time=datetime(1900,1,1,8,0,0),
        end_time=datetime(1900,1,1,9,0,0)
    ))
    p.add(Activity(
        act="work",
        loc=Point((0,1000)),
        start_time=datetime(1900,1,1,9,0,0),
        end_time=datetime(1900,1,1,18,0,0)
        ))
    p.add(Leg(
        mode='car',
        start_loc=Point((0,1000)),
        end_loc=Point((0,0)),
        start_time=datetime(1900,1,1,18,0,0),
        end_time=datetime(1900,1,1,19,0,0)
    ))
    p.add(Activity(
        act="home",
        loc=Point((0,0)),
        start_time=datetime(1900,1,1,19,0,0),
        end_time=END_OF_DAY
        ))
    hh.add(p)
    population.add(hh)
    plans_location = str(tmp_path / "test_plans.xml")
    write_v11_matsim_plans(population, path=plans_location, comment="test")
    attributes_location = str(tmp_path / "test_attributes.xml")
    write_matsim_v11_attributes(population, location=attributes_location, comment="test", household_key=None)
    new = read_matsim(
        plans_location,
        attributes_path=attributes_location,
        version=11
        )
    for hid, pid, person in population.people():
        person.plan.print()
        new[hid][pid].print()
        assert new[hid][pid].plan == person.plan
    assert new == population
    assert new['a']['a'].attributes == {'1':'1'}
    assert new['a']['a'].plan.day[1].distance == 1000


def test_write_read_continuity_xml(tmp_path, population_heh):
    plans_location = str(tmp_path / "test_plans.xml")
    write_v11_matsim_plans(population_heh, path=plans_location, comment="test")
    attributes_location = str(tmp_path / "test_attributes.xml")
    write_matsim_v11_attributes(population_heh, location=attributes_location, comment="test", household_key=None)
    population = read_matsim(
        plans_path=plans_location, attributes_path=attributes_location, household_key='hid', version=11
    )
    assert population_heh['0']['1'].plan == population['0']['1'].plan
    assert population_heh == population


def test_write_read_continuity_gzip(tmp_path, population_heh):
    plans_location = str(tmp_path / "test_plans.xml.gz")
    write_v11_matsim_plans(population_heh, path=plans_location, comment="test")
    attributes_location = str(tmp_path / "test_attributes.xml.gz")
    write_matsim_v11_attributes(population_heh, location=attributes_location, comment="test")
    population = read_matsim(
        plans_path=plans_location, attributes_path=attributes_location, household_key='hid', version=11
    )
    assert population_heh['0']['1'].plan == population['0']['1'].plan
    assert population_heh == population


def test_read_write_read_continuity_complex_xml(tmp_path):
    test_trips_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data/test_matsim_plans.xml"))
    test_attributes_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                        "test_data/test_matsim_attributes.xml"))
    population_in = read_matsim(test_trips_path, test_attributes_path, version=11)
    complex_plan_in = population_in['census_1']['census_1'].plan
    plans_location = str(tmp_path / "test_plans.xml")
    write_v11_matsim_plans(population_in, path=plans_location, comment="test")
    attributes_location = str(tmp_path / "test_attributes.xml")
    write_matsim_v11_attributes(population_in, location=attributes_location, comment="test")
    population_out = read_matsim(
        plans_path=plans_location, attributes_path=attributes_location, household_key='hid', version=11
    )
    complex_plan_out = population_out['census_1']['census_1'].plan
    assert complex_plan_in == complex_plan_out
    assert population_in == population_out


def test_write_plans_xml_v12(tmp_path, population_heh):
    location = str(tmp_path / "test.xml")
    write_matsim_v12(population=population_heh, path=location, comment="test")
    expected_file = "{}/test.xml".format(tmp_path)
    assert os.path.exists(expected_file)
    xml_obj = lxml.etree.parse(expected_file)
    dtd = write.v12_plans_dtd()
    assert dtd.validate(xml_obj), dtd.error_log.filter_from_errors()


def test_write_plans_xml_v12_gzip(tmp_path, population_heh):
    location = str(tmp_path / "test.xml.gz")
    write_matsim_v12(population=population_heh, path=location, comment="test")
    expected_file = "{}/test.xml.gz".format(tmp_path)
    assert os.path.exists(expected_file)
    # TODO make assertions about the content of the created file

def test_write_matsim_xml_v12(tmp_path, population_heh):
    location = str(tmp_path / "test.xml")
    write_matsim(population=population_heh, version=12, plans_path=location, comment="test")
    expected_file = "{}/test.xml".format(tmp_path)
    assert os.path.exists(expected_file)
    xml_obj = lxml.etree.parse(expected_file)
    dtd = write.v12_plans_dtd()
    assert dtd.validate(xml_obj), dtd.error_log.filter_from_errors()


def test_write_matsim_xml_v12_gzip(tmp_path, population_heh):
    location = str(tmp_path / "test.xml.gz")
    write_matsim(population=population_heh, version=12, plans_path=location, comment="test")
    expected_file = "{}/test.xml.gz".format(tmp_path)
    assert os.path.exists(expected_file)
    # TODO make assertions about the content of the created file


def test_write_plans_xml_v12_assert_contents(tmp_path):
    population = Population()
    hh = Household('a')
    p = Person('a', attributes={'1':'1'})
    p.add(Activity(
        act="home",
        loc=Point((0,0)),
        start_time=datetime(1900,1,1,0,0,0),
        end_time=datetime(1900,1,1,8,0,0)
        ))
    p.add(Leg(
        mode='car',
        start_loc=Point((0,0)),
        end_loc=Point((0,1000)),
        start_time=datetime(1900,1,1,8,0,0),
        end_time=datetime(1900,1,1,9,0,0)
    ))
    p.add(Activity(
        act="work",
        loc=Point((0,1000)),
        start_time=datetime(1900,1,1,9,0,0),
        end_time=datetime(1900,1,1,18,0,0)
        ))
    p.add(Leg(
        mode='car',
        start_loc=Point((0,1000)),
        end_loc=Point((0,0)),
        start_time=datetime(1900,1,1,18,0,0),
        end_time=datetime(1900,1,1,19,0,0)
    ))
    p.add(Activity(
        act="home",
        loc=Point((0,0)),
        start_time=datetime(1900,1,1,19,0,0),
        end_time=END_OF_DAY
        ))
    hh.add(p)
    population.add(hh)
    plans_location = str(tmp_path / "test_plans.xml")
    write_matsim(
        population,
        plans_path=plans_location,
        comment="test",
        version=12,
        household_key=None
        )
    new = read_matsim(
        plans_location,
        version=12
        )
    assert new == population
    assert new['a']['a'].attributes == {'1':'1'}
    assert new['a']['a'].plan.day[1].distance == 1000


def test_read_write_v12_consistent(tmp_path):
    test_tripsv12_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_data/test_matsim_plansv12.xml")
    )
    population = read_matsim(test_tripsv12_path, version=12)
    location = str(tmp_path / "test.xml.gz")
    write_matsim(
        population=population,
        version=12,
        plans_path=location,
        comment="test",
        household_key=None,
        )
    expected_file = "{}/test.xml.gz".format(tmp_path)
    population2 = read_matsim(expected_file, version=12)
    assert population == population2


def test_read_write_v12_non_selected_plans_inconsistently(tmp_path):
    test_tripsv12_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_data/test_matsim_plansv12.xml")
    )
    population = read_matsim(
        test_tripsv12_path,
        version=12,
        crop=False,
        keep_non_selected=True
        )
    location = str(tmp_path / "test.xml.gz")
    write_matsim(
        population=population,
        version=12,
        plans_path=location,
        comment="test",
        household_key=None,
        keep_non_selected=False,
        )
    expected_file = "{}/test.xml.gz".format(tmp_path)
    population2 = read_matsim(expected_file, version=12, crop=False, keep_non_selected=False)
    assert not population == population2


def test_read_write_v12_non_selected_plans_consistently(tmp_path):
    test_tripsv12_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_data/test_matsim_plansv12.xml")
    )
    population = read_matsim(
        test_tripsv12_path,
        version=12,
        crop=False,
        keep_non_selected=True
        )
    location = str(tmp_path / "test.xml.gz")
    write_matsim(
        population=population,
        version=12,
        plans_path=location,
        comment="test",
        household_key=None,
        keep_non_selected=True,
        )
    expected_file = "{}/test.xml.gz".format(tmp_path)
    population2 = read_matsim(expected_file, version=12, crop=False, keep_non_selected=True)
    assert population == population2


def test_writes_od_matrix_to_expected_file(tmpdir):
    population = Population()

    household = Household(hid = '0')
    person = Person(pid='0',  home_area='Barnet', attributes = {'occ':'white'})
    person.add(Activity(1, 'home','Barnet', start_time=mtdt(0)))
    person.add(Leg(1, mode='car', start_area='Barnet', end_area='Southwark', start_time=mtdt(400), purp='work'))
    person.add(Activity(2,'work', 'Southwark', start_time=mtdt(420)))
    person.add(Leg(2,'car', start_area='Southwark', end_area='Barnet', start_time=mtdt(1020), purp='work'))
    person.add(Activity(3,'home','Barnet',start_time=mtdt(1040), end_time=mtdt(1439)))
    household.add(person)
    population.add(household)

    household = Household(hid = '1')
    person = Person(pid='1', home_area='Ealing', attributes = {'occ':'white'})
    person.add(Activity(1, 'home','Ealing',start_time=mtdt(0)))
    person.add(Leg(1, mode='cycle', start_area='Ealing', end_area='Westminster,City of London', start_time=mtdt(500), purp='education'))
    person.add(Activity(2,'education', 'Westminster,City of London',start_time=mtdt(550)))
    person.add(Leg(2,'cycle', start_area='Westminster,City of London', end_area='Ealing', start_time=mtdt(700), purp='education'))
    person.add(Activity(3,'home','Ealing',start_time=mtdt(750), end_time=mtdt(1439)))
    household.add(person)
    population.add(household)

    household = Household(hid = '2')
    person = Person(pid='2', home_area='Ealing',attributes = {'occ':'white'})
    person.add(Activity(1, 'home','Ealing', start_time=mtdt(0)))
    person.add(Leg(1, mode='car', start_area='Ealing', end_area='Westminster,City of London', start_time=mtdt(450), purp='work'))
    person.add(Activity(2,'work', 'Westminster,City of London',start_time=mtdt(480)))
    person.add(Leg(2,'car', start_area='Westminster,City of London', end_area='Ealing', start_time=mtdt(1050), purp='work'))
    person.add(Activity(3,'home','Ealing',start_time=mtdt(1080), end_time=mtdt(1439)))
    household.add(person)
    population.add(household)

    household = Household(hid = '3')
    person = Person(pid='3', home_area='Barnet',attributes = {'occ':'blue'})
    person.add(Activity(1, 'home','Barnet', start_time = mtdt(0)))
    person.add(Leg(1, mode='walk', start_area='Barnet', end_area='Barnet', start_time=mtdt(450), purp='shop'))
    person.add(Activity(2,'shop', 'Barnet',start_time=mtdt(470)))
    person.add(Leg(2,'walk', start_area='Barnet', end_area='Barnet', start_time=mtdt(600), purp='shop'))
    person.add(Activity(3,'home','Barnet',start_time=mtdt(620), end_time=mtdt(1439)))
    household.add(person)
    population.add(household)

    household = Household(hid = '4')
    person = Person(pid='4', home_area='Ealing',attributes = {'occ':'blue'})
    person.add(Activity(1, 'home','Ealing', start_time = mtdt(0)))
    person.add(Leg(1, mode='cycle', start_area='Ealing', end_area='Ealing', start_time=mtdt(400), purp='work'))
    person.add(Activity(2,'work', 'Ealing',start_time=mtdt(420)))
    person.add(Leg(2,'cycle', start_area='Ealing', end_area='Ealing', start_time=mtdt(1030), purp='work'))
    person.add(Activity(3,'home','Ealing',start_time=mtdt(1050), end_time=mtdt(1439)))
    household.add(person)
    population.add(household)

    attribute_list = ['white', 'blue', 'total']
    mode_list = ['car', 'cycle','walk', 'total']
    time_slice = [(400, 500), (1020, 1060)]

    write_od_matrices(population, tmpdir, leg_filter = 'Mode')
    for m in mode_list:
        od_matrix_file = os.path.join(tmpdir, m+"_od.csv")
        od_matrix_csv_string = open(od_matrix_file).read()
        if m == 'car':
            expected_od_matrix = \
                    'Origin,Barnet,Ealing,Southwark,"Westminster,City of London"\n' \
                    'Barnet,0,0,1,0\n' \
                    'Ealing,0,0,0,1\n' \
                    'Southwark,1,0,0,0\n' \
                    '"Westminster,City of London",0,1,0,0\n'
            assert od_matrix_csv_string == expected_od_matrix
        if m == 'cycle':
            expected_od_matrix = \
                    'Origin,Ealing,"Westminster,City of London"\n' \
                    'Ealing,2,1\n' \
                    '"Westminster,City of London",1,0\n'
            assert od_matrix_csv_string == expected_od_matrix
        if m == 'walk':
            expected_od_matrix = \
                    'Origin,Barnet\n' \
                    'Barnet,2\n'
            assert od_matrix_csv_string == expected_od_matrix
        if m == 'total':
            expected_od_matrix = \
                    'Origin,Barnet,Ealing,Southwark,"Westminster,City of London"\n' \
                    'Barnet,2,0,1,0\n' \
                    'Ealing,0,2,0,2\n' \
                    'Southwark,1,0,0,0\n' \
                    '"Westminster,City of London",0,2,0,0\n'
            assert od_matrix_csv_string == expected_od_matrix

    write_od_matrices(population, tmpdir, person_filter = 'occ')
    for a in attribute_list:
        od_matrix_file = os.path.join(tmpdir, a+"_od.csv")
        od_matrix_csv_string = open(od_matrix_file).read()
        if a == 'white':
            expected_od_matrix = \
                    'Origin,Barnet,Ealing,Southwark,"Westminster,City of London"\n' \
                    'Barnet,0,0,1,0\n' \
                    'Ealing,0,0,0,2\n' \
                    'Southwark,1,0,0,0\n' \
                    '"Westminster,City of London",0,2,0,0\n'
            assert od_matrix_csv_string == expected_od_matrix
        if a == 'blue':
            expected_od_matrix = \
                    'Origin,Barnet,Ealing\n' \
                    'Barnet,2,0\n' \
                    'Ealing,0,2\n'
            assert od_matrix_csv_string == expected_od_matrix
        if a == 'total':
            expected_od_matrix = \
                    'Origin,Barnet,Ealing,Southwark,"Westminster,City of London"\n' \
                    'Barnet,2,0,1,0\n' \
                    'Ealing,0,2,0,2\n' \
                    'Southwark,1,0,0,0\n' \
                    '"Westminster,City of London",0,2,0,0\n'
            assert od_matrix_csv_string == expected_od_matrix

    write_od_matrices(population, tmpdir, time_minutes_filter = [(400,500),(1020,1060)])
    for start_time, end_time in time_slice:
        file_name = str(start_time) +'_to_'+ str(end_time)
        od_matrix_file = os.path.join(tmpdir,'time_'+file_name+'_od.csv' )
        od_matrix_csv_string = open(od_matrix_file).read()
        if (start_time, end_time) == (400, 500):
            expected_od_matrix = \
                    'Origin,Barnet,Ealing,Southwark,"Westminster,City of London"\n' \
                    'Barnet,1,0,1,0\n' \
                    'Ealing,0,1,0,1\n'
            assert od_matrix_csv_string == expected_od_matrix
        if (start_time, end_time) == (1020, 1060):
            expected_od_matrix = \
                    'Origin,Barnet,Ealing\n' \
                    'Ealing,0,1\n' \
                    'Southwark,1,0\n' \
                    '"Westminster,City of London",0,1\n'
            assert od_matrix_csv_string == expected_od_matrix


def test_write_to_csv_no_locs(population_heh, tmpdir):
    for _, _, person in population_heh.people():
        for act in person.activities:
            act.location.loc = None
        for leg in person.legs:
            leg.start_location.loc = None
            leg.end_location.loc = None
    population_heh.to_csv(tmpdir)

    # check csvs
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.csv"))

    hh_df = pd.read_csv(os.path.join(tmpdir, "households.csv"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone']
    assert len(hh_df) == 1

    people_df = pd.read_csv(os.path.join(tmpdir, "people.csv"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc']
    assert len(people_df) == 1

    legs_df = pd.read_csv(os.path.join(tmpdir, "legs.csv"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration'
       ]
    assert len(legs_df) == 2

    acts_df = pd.read_csv(os.path.join(tmpdir, "activities.csv"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone'
       ]
    assert len(acts_df) == 3

    # check geojson
    for name in ['households', 'people', 'legs', 'activities']:
        assert not os.path.exists(os.path.join(tmpdir, f"{name}.geojson"))


def test_write_to_csv_locs(population_heh, tmpdir):
    population_heh.to_csv(tmpdir)

    # check csvs
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.csv"))

    hh_df = pd.read_csv(os.path.join(tmpdir, "households.csv"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone']
    assert len(hh_df) == 1

    people_df = pd.read_csv(os.path.join(tmpdir, "people.csv"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc']
    assert len(people_df) == 1

    legs_df = pd.read_csv(os.path.join(tmpdir, "legs.csv"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration'
       ]
    assert len(legs_df) == 2

    acts_df = pd.read_csv(os.path.join(tmpdir, "activities.csv"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone'
       ]
    assert len(acts_df) == 3

    # check geojsons
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.geojson"))

    hh_df = gp.read_file(os.path.join(tmpdir, "households.geojson"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone', 'geometry']
    assert len(hh_df) == 1

    people_df = gp.read_file(os.path.join(tmpdir, "people.geojson"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc', 'geometry']
    assert len(people_df) == 1

    legs_df = gp.read_file(os.path.join(tmpdir, "legs.geojson"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration', 'geometry'
       ]
    assert len(legs_df) == 2

    acts_df = gp.read_file(os.path.join(tmpdir, "activities.geojson"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone', 'geometry'
       ]
    assert len(acts_df) == 3


def test_write_to_csv_some_locs(population_heh, tmpdir):
    hh1 = population_heh['0']
    hh2 = deepcopy(hh1)
    hh2.hid = '1'
    population_heh.add(hh2)

    for _, person in hh2.people.items():
        for act in person.activities:
            act.location.loc = None
        for leg in person.legs:
            leg.start_location.loc = None
            leg.end_location.loc = None
    population_heh.to_csv(tmpdir)

    # check csvs
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.csv"))

    hh_df = pd.read_csv(os.path.join(tmpdir, "households.csv"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone']
    assert len(hh_df) == 2

    people_df = pd.read_csv(os.path.join(tmpdir, "people.csv"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc']
    assert len(people_df) == 2

    legs_df = pd.read_csv(os.path.join(tmpdir, "legs.csv"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration'
       ]
    assert len(legs_df) == 4

    acts_df = pd.read_csv(os.path.join(tmpdir, "activities.csv"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone'
       ]
    assert len(acts_df) == 6

    # check geojsons
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.geojson"))

    hh_df = gp.read_file(os.path.join(tmpdir, "households.geojson"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone', 'geometry']
    assert len(hh_df) == 2

    people_df = gp.read_file(os.path.join(tmpdir, "people.geojson"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc', 'geometry']
    assert len(people_df) == 2

    legs_df = gp.read_file(os.path.join(tmpdir, "legs.geojson"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration', 'geometry'
       ]
    assert len(legs_df) == 4

    acts_df = gp.read_file(os.path.join(tmpdir, "activities.geojson"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone', 'geometry'
       ]
    assert len(acts_df) == 6


def test_write_to_csv_convert_locs(population_heh, tmpdir):
    population_heh.to_csv(tmpdir, crs="EPSG:27700")

    # check csvs
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.csv"))

    hh_df = pd.read_csv(os.path.join(tmpdir, "households.csv"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone']
    assert len(hh_df) == 1

    people_df = pd.read_csv(os.path.join(tmpdir, "people.csv"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc']
    assert len(people_df) == 1

    legs_df = pd.read_csv(os.path.join(tmpdir, "legs.csv"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration'
       ]
    assert len(legs_df) == 2

    acts_df = pd.read_csv(os.path.join(tmpdir, "activities.csv"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone'
       ]
    assert len(acts_df) == 3

    # check geojsons
    for name in ['households', 'people', 'legs', 'activities']:
        assert os.path.exists(os.path.join(tmpdir, f"{name}.geojson"))

    hh_df = gp.read_file(os.path.join(tmpdir, "households.geojson"))
    assert list(hh_df.columns) == ['hid', 'freq', 'hzone', 'geometry']
    assert len(hh_df) == 1

    people_df = gp.read_file(os.path.join(tmpdir, "people.geojson"))
    assert list(people_df.columns) == ['pid', 'hid', 'freq', 'hzone', 'hh_size', 'inc', 'geometry']
    assert len(people_df) == 1

    legs_df = gp.read_file(os.path.join(tmpdir, "legs.geojson"), index_col=0)
    assert list(legs_df.columns) == [
        'pid', 'hid', 'freq', 'ozone', 'dzone', 'purp', 'origin activity',
       'destination activity', 'mode', 'seq', 'tst', 'tet',
       'duration', 'geometry'
       ]
    assert len(legs_df) == 2

    acts_df = gp.read_file(os.path.join(tmpdir, "activities.geojson"), index_col=0)
    assert list(acts_df.columns) == [
        'pid', 'hid', 'freq', 'activity', 'seq', 'start time', 'end time',
       'duration', 'zone', 'geometry'
       ]
    assert len(acts_df) == 3


###########################################################
# helper functions
###########################################################
def get_all_people_attributes(population):
    attribute_names = set()
    for hid, pid, person in population.people():
        if person.attributes:
            for attribute_name in person.attributes.keys():
                attribute_names.add(attribute_name)
    return attribute_names


def get_ordered_legs(population_heh):
    all_legs = []
    for hid, pid, person in population_heh.people():
        for leg in list(person.legs):
            all_legs.append(((hid, pid, person), leg))
    return all_legs


def get_ordered_activities(population_heh):
    all_activities = []
    for hid, pid, person in population_heh.people():
        for activity in list(person.activities):
            all_activities.append(((hid, pid, person), activity))
    return all_activities
