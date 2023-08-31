/****************************************************************************
** Meta object code from reading C++ file 'PBitMultiDataItem.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.9.7)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "PBitMultiDataItem.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'PBitMultiDataItem.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.9.7. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_PBitMultiDataItem_t {
    QByteArrayData data[12];
    char stringdata0[124];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_PBitMultiDataItem_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_PBitMultiDataItem_t qt_meta_stringdata_PBitMultiDataItem = {
    {
QT_MOC_LITERAL(0, 0, 17), // "PBitMultiDataItem"
QT_MOC_LITERAL(1, 18, 15), // "highWordChanged"
QT_MOC_LITERAL(2, 34, 0), // ""
QT_MOC_LITERAL(3, 35, 14), // "lowWordChanged"
QT_MOC_LITERAL(4, 50, 12), // "nBitsChanged"
QT_MOC_LITERAL(5, 63, 11), // "setHighWord"
QT_MOC_LITERAL(6, 75, 8), // "highWord"
QT_MOC_LITERAL(7, 84, 5), // "force"
QT_MOC_LITERAL(8, 90, 10), // "setLowWord"
QT_MOC_LITERAL(9, 101, 7), // "lowWord"
QT_MOC_LITERAL(10, 109, 8), // "setNBits"
QT_MOC_LITERAL(11, 118, 5) // "nBits"

    },
    "PBitMultiDataItem\0highWordChanged\0\0"
    "lowWordChanged\0nBitsChanged\0setHighWord\0"
    "highWord\0force\0setLowWord\0lowWord\0"
    "setNBits\0nBits"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_PBitMultiDataItem[] = {

 // content:
       7,       // revision
       0,       // classname
       0,    0, // classinfo
       9,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       3,       // signalCount

 // signals: name, argc, parameters, tag, flags
       1,    1,   59,    2, 0x06 /* Public */,
       3,    1,   62,    2, 0x06 /* Public */,
       4,    1,   65,    2, 0x06 /* Public */,

 // slots: name, argc, parameters, tag, flags
       5,    2,   68,    2, 0x0a /* Public */,
       5,    1,   73,    2, 0x2a /* Public | MethodCloned */,
       8,    2,   76,    2, 0x0a /* Public */,
       8,    1,   81,    2, 0x2a /* Public | MethodCloned */,
      10,    2,   84,    2, 0x0a /* Public */,
      10,    1,   89,    2, 0x2a /* Public | MethodCloned */,

 // signals: parameters
    QMetaType::Void, QMetaType::QString,    2,
    QMetaType::Void, QMetaType::QString,    2,
    QMetaType::Void, QMetaType::Int,    2,

 // slots: parameters
    QMetaType::Void, QMetaType::QString, QMetaType::Bool,    6,    7,
    QMetaType::Void, QMetaType::QString,    6,
    QMetaType::Void, QMetaType::QString, QMetaType::Bool,    9,    7,
    QMetaType::Void, QMetaType::QString,    9,
    QMetaType::Void, QMetaType::Int, QMetaType::Bool,   11,    7,
    QMetaType::Void, QMetaType::Int,   11,

       0        // eod
};

void PBitMultiDataItem::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        PBitMultiDataItem *_t = static_cast<PBitMultiDataItem *>(_o);
        Q_UNUSED(_t)
        switch (_id) {
        case 0: _t->highWordChanged((*reinterpret_cast< QString(*)>(_a[1]))); break;
        case 1: _t->lowWordChanged((*reinterpret_cast< QString(*)>(_a[1]))); break;
        case 2: _t->nBitsChanged((*reinterpret_cast< int(*)>(_a[1]))); break;
        case 3: _t->setHighWord((*reinterpret_cast< QString(*)>(_a[1])),(*reinterpret_cast< bool(*)>(_a[2]))); break;
        case 4: _t->setHighWord((*reinterpret_cast< QString(*)>(_a[1]))); break;
        case 5: _t->setLowWord((*reinterpret_cast< QString(*)>(_a[1])),(*reinterpret_cast< bool(*)>(_a[2]))); break;
        case 6: _t->setLowWord((*reinterpret_cast< QString(*)>(_a[1]))); break;
        case 7: _t->setNBits((*reinterpret_cast< int(*)>(_a[1])),(*reinterpret_cast< bool(*)>(_a[2]))); break;
        case 8: _t->setNBits((*reinterpret_cast< int(*)>(_a[1]))); break;
        default: ;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            typedef void (PBitMultiDataItem::*_t)(QString );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PBitMultiDataItem::highWordChanged)) {
                *result = 0;
                return;
            }
        }
        {
            typedef void (PBitMultiDataItem::*_t)(QString );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PBitMultiDataItem::lowWordChanged)) {
                *result = 1;
                return;
            }
        }
        {
            typedef void (PBitMultiDataItem::*_t)(int );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PBitMultiDataItem::nBitsChanged)) {
                *result = 2;
                return;
            }
        }
    }
}

const QMetaObject PBitMultiDataItem::staticMetaObject = {
    { &PExtremaDataItem::staticMetaObject, qt_meta_stringdata_PBitMultiDataItem.data,
      qt_meta_data_PBitMultiDataItem,  qt_static_metacall, nullptr, nullptr}
};


const QMetaObject *PBitMultiDataItem::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *PBitMultiDataItem::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_PBitMultiDataItem.stringdata0))
        return static_cast<void*>(this);
    return PExtremaDataItem::qt_metacast(_clname);
}

int PBitMultiDataItem::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = PExtremaDataItem::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 9)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 9;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 9)
            *reinterpret_cast<int*>(_a[0]) = -1;
        _id -= 9;
    }
    return _id;
}

// SIGNAL 0
void PBitMultiDataItem::highWordChanged(QString _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 0, _a);
}

// SIGNAL 1
void PBitMultiDataItem::lowWordChanged(QString _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 1, _a);
}

// SIGNAL 2
void PBitMultiDataItem::nBitsChanged(int _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 2, _a);
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
