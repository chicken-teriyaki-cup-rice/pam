import os
import pandas as pd
from typing import Tuple, Optional, List

from pam.utils import minutes_to_datetime as mtdt
from pam.utils import create_local_dir


def write_od_matrices(
        population,
        path : str,
        leg_filter : Optional[str] = None,
        person_filter : Optional[str] = None,
        time_minutes_filter : Optional[List[Tuple[int]]] = None
        ) -> None:

    """
    Write a core population object to tabular O-D weighted matrices.
    Optionally segment matrices by leg attributes(mode/ purpose), person attributes or specific time periods.
    A single filter can be applied each time.
    TODO include freq (assume hh)

    :param population: core.Population
    :param path: directory to write OD matrix files
    :param leg_filter: select between 'Mode', 'Purpose'
    :param person_filter: select between given attribute categories (column names) from person attribute data
    :param time_minutes_filter: a list of tuples to slice times,
    e.g. [(start_of_slicer_1, end_of_slicer_1), (start_of_slicer_2, end_of_slicer_2), ... ]
    """
    create_local_dir(path)

    legs = []

    for hid, household in population.households.items():
        for pid, person in household.people.items():
            for leg in person.legs:
                data = {
                    'Household ID': hid,
                    'Person ID': pid,
                    'Origin':leg.start_location.area,
                    'Destination': leg.end_location.area,
                    'Purpose': leg.purp,
                    'Mode': leg.mode,
                    'Sequence': leg.seq,
                    'Start time': leg.start_time,
                    'End time': leg.end_time,
                    'Freq': household.freq,
                    }
                if person_filter:
                    legs.append({**data, **person.attributes})
                else:
                    legs.append(data)

    df_total = pd.DataFrame(data=legs, columns = ['Origin','Destination']).set_index('Origin')
    matrix = df_total.pivot_table(values='Destination', index='Origin', columns='Destination', fill_value=0, aggfunc=len)
    matrix.to_csv(os.path.join(path, 'total_od.csv'))

    data_legs = pd.DataFrame(data=legs)

    if leg_filter:
        data_legs_grouped=data_legs.groupby(leg_filter)
        for filter, leg in data_legs_grouped:
            df = pd.DataFrame(data=leg, columns = ['Origin','Destination']).set_index('Origin')
            matrix = df.pivot_table(values='Destination', index='Origin', columns='Destination', fill_value=0, aggfunc=len)
            matrix.to_csv(os.path.join(path, filter+'_od.csv'))
        return None

    elif person_filter:
        data_legs_grouped=data_legs.groupby(person_filter)
        for filter, leg in data_legs_grouped:
            df = pd.DataFrame(data=leg, columns = ['Origin','Destination']).set_index('Origin')
            matrix = df.pivot_table(values='Destination', index='Origin', columns='Destination', fill_value=0, aggfunc=len)
            matrix.to_csv(os.path.join(path, filter+'_od.csv'))
        return None

    elif time_minutes_filter:
        periods = []
        for time in time_minutes_filter:
            periods.append(time)
        for start_time, end_time in periods:
            file_name = str(start_time) +'_to_'+ str(end_time)
            start_time = mtdt(start_time)
            end_time = mtdt(end_time)
            data_time = data_legs[(data_legs['Start time']>= start_time)&(data_legs['Start time']< end_time)]
            df = pd.DataFrame(data=data_time, columns = ['Origin','Destination']).set_index('Origin')
            matrix = df.pivot_table(values='Destination', index='Origin', columns='Destination', fill_value=0, aggfunc=len)
            matrix.to_csv(os.path.join(path, 'time_'+file_name+'_od.csv'))
        return None

