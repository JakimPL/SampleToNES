from pydantic import BaseModel

from sampletones_application.layout.general.buttons import ButtonsLayout
from sampletones_application.layout.general.caret import CaretLayout
from sampletones_application.layout.general.collapse import CollapseLayout
from sampletones_application.layout.general.colors.colors import GeneralColors
from sampletones_application.layout.general.columns import ColumnsLayout
from sampletones_application.layout.general.dialogs.dialogs import DialogsLayout
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.general.pitch_stepper import PitchStepperLayout
from sampletones_application.layout.general.plus_minus_buttons import PlusMinusButtonsLayout
from sampletones_application.layout.general.responsive import ResponsiveLayout
from sampletones_application.layout.general.section_header import SectionHeaderLayout
from sampletones_application.layout.general.status_bar import StatusBarLayout
from sampletones_application.layout.general.tables import TablesLayout
from sampletones_application.layout.general.window import WindowLayout


class GeneralLayout(BaseModel, extra="forbid", frozen=True):
    window: WindowLayout
    panel_gap: int
    columns: ColumnsLayout
    responsive: ResponsiveLayout
    status_bar: StatusBarLayout
    dialogs: DialogsLayout
    inputs: InputsLayout
    buttons: ButtonsLayout
    tables: TablesLayout
    pitch_stepper: PitchStepperLayout
    plus_minus_buttons: PlusMinusButtonsLayout
    caret: CaretLayout
    section_header: SectionHeaderLayout
    collapse: CollapseLayout
    colors: GeneralColors
