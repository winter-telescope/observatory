/****************************************************************************
** Meta object code from reading C++ file 'PStyleChooser.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.9.7)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "PStyleChooser.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'PStyleChooser.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.9.7. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_PStyleChooser_t {
    QByteArrayData data[13];
    char stringdata0[123];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_PStyleChooser_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_PStyleChooser_t qt_meta_stringdata_PStyleChooser = {
    {
QT_MOC_LITERAL(0, 0, 13), // "PStyleChooser"
QT_MOC_LITERAL(1, 14, 19), // "setNoWidgetStyleRef"
QT_MOC_LITERAL(2, 34, 0), // ""
QT_MOC_LITERAL(3, 35, 17), // "setWidgetStyleRef"
QT_MOC_LITERAL(4, 53, 8), // "PStyle*&"
QT_MOC_LITERAL(5, 62, 5), // "style"
QT_MOC_LITERAL(6, 68, 6), // "select"
QT_MOC_LITERAL(7, 75, 1), // "s"
QT_MOC_LITERAL(8, 77, 9), // "boldLogic"
QT_MOC_LITERAL(9, 87, 11), // "italicLogic"
QT_MOC_LITERAL(10, 99, 7), // "fgLogic"
QT_MOC_LITERAL(11, 107, 7), // "bgLogic"
QT_MOC_LITERAL(12, 115, 7) // "refresh"

    },
    "PStyleChooser\0setNoWidgetStyleRef\0\0"
    "setWidgetStyleRef\0PStyle*&\0style\0"
    "select\0s\0boldLogic\0italicLogic\0fgLogic\0"
    "bgLogic\0refresh"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_PStyleChooser[] = {

 // content:
       7,       // revision
       0,       // classname
       0,    0, // classinfo
       8,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    0,   54,    2, 0x0a /* Public */,
       3,    1,   55,    2, 0x0a /* Public */,
       6,    1,   58,    2, 0x0a /* Public */,
       8,    1,   61,    2, 0x0a /* Public */,
       9,    1,   64,    2, 0x0a /* Public */,
      10,    0,   67,    2, 0x0a /* Public */,
      11,    0,   68,    2, 0x0a /* Public */,
      12,    0,   69,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void, 0x80000000 | 4,    5,
    QMetaType::Void, QMetaType::QString,    7,
    QMetaType::Void, QMetaType::Bool,    2,
    QMetaType::Void, QMetaType::Bool,    2,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void PStyleChooser::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        PStyleChooser *_t = static_cast<PStyleChooser *>(_o);
        Q_UNUSED(_t)
        switch (_id) {
        case 0: _t->setNoWidgetStyleRef(); break;
        case 1: _t->setWidgetStyleRef((*reinterpret_cast< PStyle*(*)>(_a[1]))); break;
        case 2: _t->select((*reinterpret_cast< QString(*)>(_a[1]))); break;
        case 3: _t->boldLogic((*reinterpret_cast< bool(*)>(_a[1]))); break;
        case 4: _t->italicLogic((*reinterpret_cast< bool(*)>(_a[1]))); break;
        case 5: _t->fgLogic(); break;
        case 6: _t->bgLogic(); break;
        case 7: _t->refresh(); break;
        default: ;
        }
    }
}

const QMetaObject PStyleChooser::staticMetaObject = {
    { &QWidget::staticMetaObject, qt_meta_stringdata_PStyleChooser.data,
      qt_meta_data_PStyleChooser,  qt_static_metacall, nullptr, nullptr}
};


const QMetaObject *PStyleChooser::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *PStyleChooser::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_PStyleChooser.stringdata0))
        return static_cast<void*>(this);
    return QWidget::qt_metacast(_clname);
}

int PStyleChooser::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QWidget::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 8)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 8;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 8)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 8;
    }
    return _id;
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
