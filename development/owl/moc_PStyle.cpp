/****************************************************************************
** Meta object code from reading C++ file 'PStyle.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.9.7)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "PStyle.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'PStyle.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.9.7. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_PStyleNotifier_t {
    QByteArrayData data[6];
    char stringdata0[51];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_PStyleNotifier_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_PStyleNotifier_t qt_meta_stringdata_PStyleNotifier = {
    {
QT_MOC_LITERAL(0, 0, 14), // "PStyleNotifier"
QT_MOC_LITERAL(1, 15, 6), // "change"
QT_MOC_LITERAL(2, 22, 0), // ""
QT_MOC_LITERAL(3, 23, 7), // "disable"
QT_MOC_LITERAL(4, 31, 6), // "enable"
QT_MOC_LITERAL(5, 38, 12) // "notifyChange"

    },
    "PStyleNotifier\0change\0\0disable\0enable\0"
    "notifyChange"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_PStyleNotifier[] = {

 // content:
       7,       // revision
       0,       // classname
       0,    0, // classinfo
       4,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       1,       // signalCount

 // signals: name, argc, parameters, tag, flags
       1,    0,   34,    2, 0x06 /* Public */,

 // slots: name, argc, parameters, tag, flags
       3,    0,   35,    2, 0x0a /* Public */,
       4,    0,   36,    2, 0x0a /* Public */,
       5,    0,   37,    2, 0x0a /* Public */,

 // signals: parameters
    QMetaType::Void,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void PStyleNotifier::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        PStyleNotifier *_t = static_cast<PStyleNotifier *>(_o);
        Q_UNUSED(_t)
        switch (_id) {
        case 0: _t->change(); break;
        case 1: _t->disable(); break;
        case 2: _t->enable(); break;
        case 3: _t->notifyChange(); break;
        default: ;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            typedef void (PStyleNotifier::*_t)();
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PStyleNotifier::change)) {
                *result = 0;
                return;
            }
        }
    }
    Q_UNUSED(_a);
}

const QMetaObject PStyleNotifier::staticMetaObject = {
    { &QObject::staticMetaObject, qt_meta_stringdata_PStyleNotifier.data,
      qt_meta_data_PStyleNotifier,  qt_static_metacall, nullptr, nullptr}
};


const QMetaObject *PStyleNotifier::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *PStyleNotifier::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_PStyleNotifier.stringdata0))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int PStyleNotifier::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 4)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 4;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 4)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 4;
    }
    return _id;
}

// SIGNAL 0
void PStyleNotifier::change()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}
struct qt_meta_stringdata_PStyle_t {
    QByteArrayData data[10];
    char stringdata0[55];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_PStyle_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_PStyle_t qt_meta_stringdata_PStyle = {
    {
QT_MOC_LITERAL(0, 0, 6), // "PStyle"
QT_MOC_LITERAL(1, 7, 7), // "setName"
QT_MOC_LITERAL(2, 15, 0), // ""
QT_MOC_LITERAL(3, 16, 4), // "name"
QT_MOC_LITERAL(4, 21, 7), // "setBold"
QT_MOC_LITERAL(5, 29, 1), // "t"
QT_MOC_LITERAL(6, 31, 9), // "setItalic"
QT_MOC_LITERAL(7, 41, 5), // "setBg"
QT_MOC_LITERAL(8, 47, 1), // "c"
QT_MOC_LITERAL(9, 49, 5) // "setFg"

    },
    "PStyle\0setName\0\0name\0setBold\0t\0setItalic\0"
    "setBg\0c\0setFg"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_PStyle[] = {

 // content:
       7,       // revision
       0,       // classname
       0,    0, // classinfo
       5,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // slots: name, argc, parameters, tag, flags
       1,    1,   39,    2, 0x0a /* Public */,
       4,    1,   42,    2, 0x0a /* Public */,
       6,    1,   45,    2, 0x0a /* Public */,
       7,    1,   48,    2, 0x0a /* Public */,
       9,    1,   51,    2, 0x0a /* Public */,

 // slots: parameters
    QMetaType::Void, QMetaType::QString,    3,
    QMetaType::Void, QMetaType::Bool,    5,
    QMetaType::Void, QMetaType::Bool,    5,
    QMetaType::Void, QMetaType::QColor,    8,
    QMetaType::Void, QMetaType::QColor,    8,

       0        // eod
};

void PStyle::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        PStyle *_t = static_cast<PStyle *>(_o);
        Q_UNUSED(_t)
        switch (_id) {
        case 0: _t->setName((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 1: _t->setBold((*reinterpret_cast< const bool(*)>(_a[1]))); break;
        case 2: _t->setItalic((*reinterpret_cast< const bool(*)>(_a[1]))); break;
        case 3: _t->setBg((*reinterpret_cast< const QColor(*)>(_a[1]))); break;
        case 4: _t->setFg((*reinterpret_cast< const QColor(*)>(_a[1]))); break;
        default: ;
        }
    }
}

const QMetaObject PStyle::staticMetaObject = {
    { &QObject::staticMetaObject, qt_meta_stringdata_PStyle.data,
      qt_meta_data_PStyle,  qt_static_metacall, nullptr, nullptr}
};


const QMetaObject *PStyle::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *PStyle::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_PStyle.stringdata0))
        return static_cast<void*>(this);
    if (!strcmp(_clname, "PObject"))
        return static_cast< PObject*>(this);
    return QObject::qt_metacast(_clname);
}

int PStyle::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 5)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 5;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 5)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 5;
    }
    return _id;
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
