/****************************************************************************
** Meta object code from reading C++ file 'PMdiArea.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.9.7)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "PMdiArea.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'PMdiArea.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.9.7. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_PMdiArea_t {
    QByteArrayData data[12];
    char stringdata0[83];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_PMdiArea_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_PMdiArea_t qt_meta_stringdata_PMdiArea = {
    {
QT_MOC_LITERAL(0, 0, 8), // "PMdiArea"
QT_MOC_LITERAL(1, 9, 6), // "newBox"
QT_MOC_LITERAL(2, 16, 0), // ""
QT_MOC_LITERAL(3, 17, 5), // "PBox*"
QT_MOC_LITERAL(4, 23, 6), // "newOwl"
QT_MOC_LITERAL(5, 30, 14), // "POwlAnimation*"
QT_MOC_LITERAL(6, 45, 10), // "createPBox"
QT_MOC_LITERAL(7, 56, 1), // "x"
QT_MOC_LITERAL(8, 58, 1), // "y"
QT_MOC_LITERAL(9, 60, 6), // "c_pbox"
QT_MOC_LITERAL(10, 67, 9), // "createOwl"
QT_MOC_LITERAL(11, 77, 5) // "c_owl"

    },
    "PMdiArea\0newBox\0\0PBox*\0newOwl\0"
    "POwlAnimation*\0createPBox\0x\0y\0c_pbox\0"
    "createOwl\0c_owl"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_PMdiArea[] = {

 // content:
       7,       // revision
       0,       // classname
       0,    0, // classinfo
      10,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       2,       // signalCount

 // signals: name, argc, parameters, tag, flags
       1,    1,   64,    2, 0x06 /* Public */,
       4,    1,   67,    2, 0x06 /* Public */,

 // slots: name, argc, parameters, tag, flags
       6,    3,   70,    2, 0x0a /* Public */,
       6,    2,   77,    2, 0x2a /* Public | MethodCloned */,
       6,    1,   82,    2, 0x2a /* Public | MethodCloned */,
       6,    0,   85,    2, 0x2a /* Public | MethodCloned */,
      10,    3,   86,    2, 0x0a /* Public */,
      10,    2,   93,    2, 0x2a /* Public | MethodCloned */,
      10,    1,   98,    2, 0x2a /* Public | MethodCloned */,
      10,    0,  101,    2, 0x2a /* Public | MethodCloned */,

 // signals: parameters
    QMetaType::Void, 0x80000000 | 3,    2,
    QMetaType::Void, 0x80000000 | 5,    2,

 // slots: parameters
    QMetaType::Void, QMetaType::Int, QMetaType::Int, 0x80000000 | 3,    7,    8,    9,
    QMetaType::Void, QMetaType::Int, QMetaType::Int,    7,    8,
    QMetaType::Void, QMetaType::Int,    7,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int, QMetaType::Int, 0x80000000 | 5,    7,    8,   11,
    QMetaType::Void, QMetaType::Int, QMetaType::Int,    7,    8,
    QMetaType::Void, QMetaType::Int,    7,
    QMetaType::Void,

       0        // eod
};

void PMdiArea::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        PMdiArea *_t = static_cast<PMdiArea *>(_o);
        Q_UNUSED(_t)
        switch (_id) {
        case 0: _t->newBox((*reinterpret_cast< PBox*(*)>(_a[1]))); break;
        case 1: _t->newOwl((*reinterpret_cast< POwlAnimation*(*)>(_a[1]))); break;
        case 2: _t->createPBox((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< PBox*(*)>(_a[3]))); break;
        case 3: _t->createPBox((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2]))); break;
        case 4: _t->createPBox((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 5: _t->createPBox(); break;
        case 6: _t->createOwl((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2])),(*reinterpret_cast< POwlAnimation*(*)>(_a[3]))); break;
        case 7: _t->createOwl((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2]))); break;
        case 8: _t->createOwl((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 9: _t->createOwl(); break;
        default: ;
        }
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<int*>(_a[0]) = -1; break;
        case 0:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<int*>(_a[0]) = -1; break;
            case 0:
                *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< PBox* >(); break;
            }
            break;
        case 1:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<int*>(_a[0]) = -1; break;
            case 0:
                *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< POwlAnimation* >(); break;
            }
            break;
        case 2:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<int*>(_a[0]) = -1; break;
            case 2:
                *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< PBox* >(); break;
            }
            break;
        case 6:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<int*>(_a[0]) = -1; break;
            case 2:
                *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< POwlAnimation* >(); break;
            }
            break;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            typedef void (PMdiArea::*_t)(PBox * );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PMdiArea::newBox)) {
                *result = 0;
                return;
            }
        }
        {
            typedef void (PMdiArea::*_t)(POwlAnimation * );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PMdiArea::newOwl)) {
                *result = 1;
                return;
            }
        }
    }
}

const QMetaObject PMdiArea::staticMetaObject = {
    { &QWidget::staticMetaObject, qt_meta_stringdata_PMdiArea.data,
      qt_meta_data_PMdiArea,  qt_static_metacall, nullptr, nullptr}
};


const QMetaObject *PMdiArea::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *PMdiArea::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_PMdiArea.stringdata0))
        return static_cast<void*>(this);
    if (!strcmp(_clname, "PObject"))
        return static_cast< PObject*>(this);
    return QWidget::qt_metacast(_clname);
}

int PMdiArea::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QWidget::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 10)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 10;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 10)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 10;
    }
    return _id;
}

// SIGNAL 0
void PMdiArea::newBox(PBox * _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 0, _a);
}

// SIGNAL 1
void PMdiArea::newOwl(POwlAnimation * _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 1, _a);
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
