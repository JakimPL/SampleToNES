from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.success import ExportSuccess

ExportResult = ExportSuccess | ExportError
